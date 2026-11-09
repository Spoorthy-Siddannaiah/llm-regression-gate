"""Recorder trust-boundary regressions. Providers are mocked; no model calls."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

import pytest

from llm_reliability.generation import MODEL_DIGEST
from llm_reliability.loading import InputLoadError, load_comparison
from llm_reliability.gates import compare_and_gate
from llm_reliability.reports import render_markdown

ROOT = Path(__file__).resolve().parents[1]
MARKER = "FICTIONAL_SENSITIVE_AUDIT_MARKER"


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.json"
    sources = tmp_path / "sources.json"
    dataset.write_bytes((ROOT / "datasets/support_policy/v1/dataset.json").read_bytes())
    sources.write_bytes((ROOT / "datasets/support_policy/v1/sources.json").read_bytes())
    output = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["record_ollama.py", "--dataset", str(dataset),
        "--sources", str(sources), "--output-dir", str(output), "--recording-id", "audit-mock"])

    def run(respond):
        class Client:
            def verify_model(self):
                return {"name": "llama3.2:latest", "digest": MODEL_DIGEST}

            def request(self, path, payload=None):
                return respond(payload) if path == "/api/chat" else {"version": "mock"}

        monkeypatch.setattr("llm_reliability.generation.LocalOllama", Client)
        runpy.run_path(str(ROOT / "scripts/record_ollama.py"), run_name="__main__")
    return dataset, sources, output, run


def response():
    return {"done": True, "done_reason": "stop", "message": {"role": "assistant",
        "content": json.dumps({"answer": "audit answer", "cited_source_ids": []})}}


@pytest.mark.parametrize("target", ["dataset", "sources", "deleted_sources"])
def test_input_drift_never_completes_and_replay_rejects_partial_run(recorder, target):
    dataset, sources, output, run = recorder
    seen = []
    original = sources.read_bytes()

    def respond(payload):
        seen.append(payload)
        if len(seen) == 1:
            if target == "dataset":
                value = json.loads(dataset.read_text())
                value["cases"][1]["question"] = "Changed question"
                dataset.write_text(json.dumps(value))
            elif target == "sources":
                sources.write_text(json.dumps({"refund-policy-v1": "Changed policy", "support-hours-v1": "Changed hours"}))
            else:
                sources.unlink()
        return response()

    with pytest.raises(SystemExit) as error:
        run(respond)
    assert error.value.code == 2
    assert len(seen) == 2
    assert json.loads(seen[1]["messages"][1]["content"])["question"] != "Changed question"
    old_texts = set(json.loads(original).values())
    assert all(s["text"] in old_texts for p in seen for s in json.loads(p["messages"][1]["content"])["sources"])
    assert (output / "evidence/002.response.json").exists()
    assert not (output / "manifest.json").exists()
    with pytest.raises(InputLoadError):
        load_comparison(dataset, output / "recording.json", output / "recording.json", require_manifests=True)


def test_manifest_binds_exact_snapshot_and_strict_replay(recorder):
    dataset, sources, output, run = recorder
    before = {"dataset": hashlib.sha256(dataset.read_bytes()).hexdigest(),
              "sources": hashlib.sha256(sources.read_bytes()).hexdigest()}
    run(lambda payload: response())
    assert json.loads((output / "manifest.json").read_text())["input_sha256"] == before
    load_comparison(dataset, output / "recording.json", output / "recording.json", sources_path=sources, require_manifests=True)
    sources.write_bytes(sources.read_bytes() + b"\n")
    with pytest.raises(InputLoadError, match="SHA-256 mismatch"):
        load_comparison(dataset, output / "recording.json", output / "recording.json", sources_path=sources)


@pytest.mark.parametrize("problem", ["extra", "duplicate", "malformed", "reason", "transport", "unexpected"])
def test_provider_failures_never_expose_values_in_console_or_error_artifacts(recorder, capsys, problem):
    _, _, output, run = recorder

    def respond(payload):
        raw = response()
        if problem == "transport":
            raise OSError(MARKER)
        if problem == "unexpected":
            raise RuntimeError(MARKER)
        if problem == "reason":
            raw["done_reason"] = MARKER
        elif problem == "malformed":
            raw["message"]["content"] = MARKER
        else:
            body = {"answer": MARKER, "cited_source_ids": [MARKER, MARKER] if problem == "duplicate" else []}
            if problem == "extra":
                body[MARKER] = MARKER
            raw["message"]["content"] = json.dumps(body)
        return raw

    with pytest.raises(SystemExit) as error:
        run(respond)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert MARKER not in captured.out + captured.err
    assert "recording_failed stage=generation_case_1" in captured.err
    assert not (output / "manifest.json").exists()
    assert not list(output.glob('*error*'))
    # Raw evidence is intentionally retained separately, never printed as an error.


@pytest.mark.parametrize("real", [False, True])
def test_report_origin_is_neutral_for_real_and_synthetic_recordings(real):
    dataset = ROOT / ("datasets/squad/v1/dataset.json" if real else "datasets/support_policy/v1/dataset.json")
    recording = ROOT / ("recordings/squad/llama3.2-bm25-v1/recording.json" if real else "recordings/baseline.synthetic.v1.json")
    text = render_markdown(compare_and_gate(load_comparison(dataset, recording, recording)))
    assert "bundled recordings are synthetic" not in text
    assert "consult recording provenance" in text
