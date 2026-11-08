import json
from pathlib import Path
import runpy
import sys

import pytest
from pydantic import ValidationError

from llm_reliability.generation import (
    LocalOllama, MODEL_DIGEST, build_request, parse_answer,
)
from llm_reliability.loading import load_recording
from llm_reliability.retrieval import RetrievalHit


def envelope(answer="unit answer", citations=None, reason="stop"):
    return {
        "done": True, "done_reason": reason,
        "message": {"role": "assistant", "content": json.dumps({
            "answer": answer, "cited_source_ids": citations or [],
        })},
        "eval_count": 10,
    }


def test_prompt_receives_only_question_and_retrieved_evidence():
    hit = RetrievalHit(source_id="source-a", text="Passage text", score=1.0)
    payload = build_request("Question?", (hit,))
    content = json.loads(payload["messages"][1]["content"])
    assert content == {"question": "Question?", "sources": [
        {"source_id": "source-a", "text": "Passage text"},
    ]}
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.0
    assert payload["format"]["additionalProperties"] is False


def test_unknown_citations_and_empty_answers_are_preserved():
    answer = parse_answer(envelope(answer="", citations=["unknown-source"]))
    assert answer.answer == ""
    assert answer.cited_source_ids == ["unknown-source"]


@pytest.mark.parametrize("problem", ["truncated", "unfinished", "malformed", "duplicate", "wrong_role"])
def test_invalid_generation_is_not_silently_recorded(problem):
    raw = envelope()
    if problem == "truncated":
        raw["done_reason"] = "length"
    elif problem == "unfinished":
        raw["done"] = False
    elif problem == "malformed":
        raw["message"]["content"] = "not JSON"
    elif problem == "duplicate":
        raw = envelope(citations=["same", "same"])
    else:
        raw["message"]["role"] = "user"
    with pytest.raises((ValueError, ValidationError)):
        parse_answer(raw)


def test_changed_or_missing_model_digest_rejected(monkeypatch):
    client = LocalOllama()
    monkeypatch.setattr(client, "request", lambda *args: {"models": []})
    with pytest.raises(ValueError, match="pinned digest"):
        client.verify_model()
    monkeypatch.setattr(client, "request", lambda *args: {"models": [
        {"name": "llama3.2:latest", "digest": "different"},
    ]})
    with pytest.raises(ValueError, match="pinned digest"):
        client.verify_model()


def test_unsupported_endpoint_rejected_before_network():
    with pytest.raises(ValueError, match="unsupported"):
        LocalOllama().request("/api/pull", {"model": "anything"})


@pytest.mark.parametrize("top_k", [1, 3])
def test_recorder_writes_evidence_and_never_overwrites(tmp_path, monkeypatch, top_k):
    root = Path(__file__).resolve().parents[1]
    verified = []

    class FakeLocalOllama:
        def verify_model(self):
            verified.append(True)
            return {"name": "llama3.2:latest", "digest": MODEL_DIGEST}

        def request(self, path, payload=None):
            if path == "/api/chat":
                return envelope(citations=["unlabelled-test-citation"])
            return {"version": "unit-test-no-server"}

    monkeypatch.setattr("llm_reliability.generation.LocalOllama", FakeLocalOllama)
    output = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", [
        "record_ollama.py", "--dataset", str(root / "datasets/squad/v1/dataset.json"),
        "--sources", str(root / "datasets/squad/v1/sources.json"), "--output-dir", str(output),
        "--recording-id", "unit-test-not-model-output", "--limit", "1", "--top-k", str(top_k),
    ])
    script = str(root / "scripts/record_ollama.py")
    runpy.run_path(script, run_name="__main__")
    recording = load_recording(output / "recording.json")
    assert recording.responses[0].cited_source_ids == ["unlabelled-test-citation"]
    assert recording.responses[0].answer == "unit answer"
    assert len(recording.responses[0].retrieved_source_ids) == top_k
    assert recording.configuration.retrieval_version == f"bm25-v1-top{top_k}"
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["scope"] == "smoke_subset"
    assert manifest["status"] == "completed_not_promoted"
    assert manifest["retrieval_top_k"] == top_k
    assert manifest["code_provenance"]["source_sha256"]["scripts/record_ollama.py"]
    assert "code-provenance.json" in manifest["artifact_sha256"]
    assert json.loads((output / "code-provenance.json").read_text()) == manifest["code_provenance"]
    assert len(verified) == 2
    assert (output / "evidence/001.request.json").exists()
    assert (output / "evidence/001.response.json").exists()
    before = (output / "recording.json").read_bytes()
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(script, run_name="__main__")
    assert caught.value.code == 2
    assert (output / "recording.json").read_bytes() == before


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_retrieval_budget_rejected_before_model_call(tmp_path, monkeypatch, top_k):
    root = Path(__file__).resolve().parents[1]

    def unexpected_client():
        raise AssertionError("invalid arguments must not contact Ollama")

    monkeypatch.setattr("llm_reliability.generation.LocalOllama", unexpected_client)
    output = tmp_path / "invalid-run"
    monkeypatch.setattr(sys, "argv", [
        "record_ollama.py", "--dataset", str(root / "datasets/squad/v1/dataset.json"),
        "--sources", str(root / "datasets/squad/v1/sources.json"), "--output-dir", str(output),
        "--recording-id", "invalid", "--top-k", str(top_k),
    ])
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(str(root / "scripts/record_ollama.py"), run_name="__main__")
    assert caught.value.code == 2
    assert not output.exists()


def test_source_drift_leaves_evidence_without_completed_recording(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]

    class FakeLocalOllama:
        def verify_model(self):
            return {"name": "llama3.2:latest", "digest": MODEL_DIGEST}

        def request(self, path, payload=None):
            return envelope() if path == "/api/chat" else {"version": "unit-test"}

    def source_changed(*args):
        raise ValueError("generation source files changed during run")

    monkeypatch.setattr("llm_reliability.generation.LocalOllama", FakeLocalOllama)
    monkeypatch.setattr("llm_reliability.run_provenance.verify_generation_sources", source_changed)
    output = tmp_path / "incomplete"
    monkeypatch.setattr(sys, "argv", [
        "record_ollama.py", "--dataset", str(root / "datasets/squad/v1/dataset.json"),
        "--sources", str(root / "datasets/squad/v1/sources.json"), "--output-dir", str(output),
        "--recording-id", "incomplete-unit-test", "--limit", "1",
    ])
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(str(root / "scripts/record_ollama.py"), run_name="__main__")
    assert caught.value.code == 2
    assert (output / "evidence/001.response.json").exists()
    assert not (output / "recording.json").exists()
    assert not (output / "manifest.json").exists()
