import hashlib
import json
from pathlib import Path

import pytest

from llm_reliability.generation import parse_answer
from llm_reliability.loading import load_corpus, load_dataset, load_recording
from llm_reliability.models import ComparisonInput
from llm_reliability.retrieval import BM25Retriever


ROOT = Path(__file__).resolve().parents[1]
@pytest.fixture(params=["llama3.2-bm25-v1", "llama3.2-bm25-top1-v1"])
def run_dir(request):
    return ROOT / "recordings/squad" / request.param


def test_actual_recording_is_complete_and_matches_evidence(run_dir):
    dataset = load_dataset(ROOT / "datasets/squad/v1/dataset.json")
    recording = load_recording(run_dir / "recording.json")
    # Compatibility self-check, not evidence of quality or improvement.
    ComparisonInput(dataset=dataset, baseline=recording, candidate=recording)
    assert len(recording.responses) == 25
    for number, observation in enumerate(recording.responses, 1):
        raw = json.loads((run_dir / f"evidence/{number:03d}.response.json").read_text())
        request = json.loads((run_dir / f"evidence/{number:03d}.request.json").read_text())
        generated = parse_answer(raw["response"])
        assert observation.case_id == raw["case_id"] == request["case_id"]
        assert observation.answer == generated.answer
        assert observation.cited_source_ids == generated.cited_source_ids
        prompt = json.loads(request["request"]["messages"][1]["content"])
        assert set(prompt) == {"question", "sources"}
        assert observation.retrieved_source_ids == [item["source_id"] for item in prompt["sources"]]


def test_actual_run_provenance_and_artifact_hashes(run_dir):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["scope"] == "full_dataset"
    assert manifest["status"] == "completed_not_promoted"
    assert manifest["case_count"] == 25
    for name, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((run_dir / name).read_bytes()).hexdigest() == digest
    for key, name in (("dataset", "dataset.json"), ("sources", "sources.json")):
        assert manifest["input_sha256"][key] == hashlib.sha256(
            (ROOT / "datasets/squad/v1" / name).read_bytes()
        ).hexdigest()


def test_actual_recording_used_real_rankings_and_corpus_text(run_dir):
    dataset = load_dataset(ROOT / "datasets/squad/v1/dataset.json")
    corpus = load_corpus(ROOT / "datasets/squad/v1/sources.json")
    retriever = BM25Retriever(corpus)
    recording = load_recording(run_dir / "recording.json")
    top_k = json.loads((run_dir / "manifest.json").read_text())["retrieval_top_k"]
    cases = {case.case_id: case for case in dataset.cases}
    for number, observation in enumerate(recording.responses, 1):
        hits = retriever.retrieve(cases[observation.case_id].question, top_k=top_k)
        assert observation.retrieved_source_ids == [hit.source_id for hit in hits]
        request = json.loads((run_dir / f"evidence/{number:03d}.request.json").read_text())
        prompt = json.loads(request["request"]["messages"][1]["content"])
        assert prompt["question"] == cases[observation.case_id].question
        for item in prompt["sources"]:
            assert item["text"] == corpus.root[item["source_id"]]
