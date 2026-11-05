import json
from pathlib import Path

import pytest

from llm_reliability.loading import (
    InputLoadError, load_comparison, load_dataset, load_recording,
)
from llm_reliability.models import Dataset, Recording


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets/support_policy/v1/dataset.json"
BASELINE = ROOT / "recordings/baseline.synthetic.v1.json"
CANDIDATE = ROOT / "recordings/candidate.synthetic.v2.json"


def test_repository_fixtures_load_without_writing():
    paths = (DATASET, BASELINE, CANDIDATE)
    before = [path.read_bytes() for path in paths]
    comparison = load_comparison(*paths)
    assert isinstance(comparison.dataset, Dataset)
    assert isinstance(comparison.baseline, Recording)
    assert comparison.baseline.responses[0].case_id == "refund-window"
    assert "30 days" in comparison.baseline.responses[0].answer
    assert "60 days" in comparison.candidate.responses[0].answer
    assert comparison.baseline.responses[1] == comparison.candidate.responses[1]
    assert [path.read_bytes() for path in paths] == before


@pytest.mark.parametrize("loader", [load_dataset, load_recording])
@pytest.mark.parametrize("problem", ["missing", "malformed", "encoding", "wrong_root"])
def test_unreadable_or_malformed_files_identify_path(tmp_path, loader, problem):
    path = tmp_path / "bad.json"
    if problem == "malformed":
        path.write_text('{"broken":', encoding="utf-8")
    elif problem == "encoding":
        path.write_bytes(b"\xff")
    elif problem == "wrong_root":
        path.write_text("[]", encoding="utf-8")
    with pytest.raises(InputLoadError) as caught:
        loader(path)
    assert str(path) in str(caught.value)
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("role", ["baseline", "candidate"])
@pytest.mark.parametrize("problem", ["duplicate", "version", "identity", "missing", "extra", "field"])
def test_recording_errors_are_actionable(tmp_path, role, problem):
    data = json.loads(CANDIDATE.read_text())
    if problem == "duplicate":
        data["responses"].append(data["responses"][0].copy())
        expected = "duplicate response case IDs: ['refund-window']"
    elif problem == "version":
        data["dataset_version"] = "999"
        expected = f"{role}: incompatible"
    elif problem == "identity":
        data["dataset_id"] = "another-dataset"
        expected = f"{role}: incompatible"
    elif problem == "missing":
        data["responses"].pop()
        expected = "missing=['support-hours']"
    elif problem == "extra":
        data["responses"].append({**data["responses"][0], "case_id": "unknown-case"})
        expected = "unexpected=['unknown-case']"
    else:
        data["responses"][0]["answer"] = 42
        expected = "responses.0.answer"
    path = tmp_path / f"{role}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputLoadError) as caught:
        load_comparison(DATASET, path if role == "baseline" else BASELINE,
                        path if role == "candidate" else CANDIDATE)
    assert str(path) in str(caught.value)
    assert expected in str(caught.value)


def test_duplicate_dataset_case_reports_file_and_case(tmp_path):
    data = json.loads(DATASET.read_text())
    data["cases"].append(data["cases"][0].copy())
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputLoadError) as caught:
        load_dataset(path)
    assert str(path) in str(caught.value)
    assert "duplicate dataset case IDs: ['refund-window']" in str(caught.value)


def test_empty_answers_and_unknown_citations_survive_comparison_loading(tmp_path):
    data = json.loads(CANDIDATE.read_text())
    data["responses"][0]["answer"] = ""
    data["responses"][0]["cited_source_ids"] = ["unknown-source"]
    data["responses"][0]["retrieved_source_ids"] = ["unknown-source", "refund-policy-v1"]
    path = tmp_path / "observations.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = load_comparison(DATASET, BASELINE, path).candidate.responses[0]
    assert result.answer == ""
    assert result.cited_source_ids == ["unknown-source"]
    assert result.retrieved_source_ids == ["unknown-source", "refund-policy-v1"]
