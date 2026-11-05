import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_reliability.models import ComparisonInput, Dataset


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def payload():
    dataset = json.loads((ROOT / "datasets/support_policy/v1/dataset.json").read_text())
    recording = {
        "recording_id": "baseline-v1",
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "configuration": {
            "configuration_id": "mock-support",
            "configuration_version": "1",
            "model_version": "mock-v1",
            "prompt_version": "1",
            "retrieval_version": "1",
        },
        "responses": [
            {"case_id": case["case_id"], "answer": "", "cited_source_ids": [],
             "retrieved_source_ids": []}
            for case in dataset["cases"]
        ],
    }
    candidate = deepcopy(recording)
    candidate["recording_id"] = "candidate-v2"
    candidate["configuration"]["prompt_version"] = "2"
    return {"dataset": dataset, "baseline": recording, "candidate": candidate}


def validate(payload):
    # JSON is the external fixture format; strict enums accept JSON string values.
    return ComparisonInput.model_validate_json(json.dumps(payload))


def test_valid_comparison_accepts_changed_configuration_without_modifying_baseline(payload):
    original = deepcopy(payload)
    result = validate(payload)
    assert result.candidate.configuration.prompt_version == "2"
    assert result.baseline.configuration.prompt_version == "1"
    assert payload == original


@pytest.mark.parametrize("role", ["baseline", "candidate"])
@pytest.mark.parametrize("problem", ["missing", "unexpected", "duplicate", "version", "identity"])
def test_invalid_recordings_are_explicit_errors(payload, role, problem):
    recording = payload[role]
    if problem == "missing":
        recording["responses"].pop()
    elif problem == "unexpected":
        recording["responses"][0]["case_id"] = "unknown"
    elif problem == "duplicate":
        recording["responses"].append(deepcopy(recording["responses"][0]))
    elif problem == "version":
        recording["dataset_version"] = "2"
    else:
        recording["dataset_id"] = "different"
    with pytest.raises(ValidationError, match="duplicate|coverage mismatch|incompatible"):
        validate(payload)


@pytest.mark.parametrize("problem", ["duplicate", "blank", "empty", "unknown_field", "schema"])
def test_invalid_datasets_are_rejected(payload, problem):
    dataset = payload["dataset"]
    if problem == "duplicate":
        dataset["cases"].append(deepcopy(dataset["cases"][0]))
    elif problem == "blank":
        dataset["cases"][0]["case_id"] = "  "
    elif problem == "empty":
        dataset["cases"] = []
    elif problem == "unknown_field":
        dataset["versoin"] = "1"
    else:
        dataset["schema_version"] = 2
    with pytest.raises(ValidationError):
        validate(payload)


def test_ranked_sources_preserve_order_and_unknown_citations_are_scoreable(payload):
    response = payload["candidate"]["responses"][0]
    response["retrieved_source_ids"] = ["other-source", "refund-policy-v1"]
    response["cited_source_ids"] = ["nonexistent-source"]
    result = validate(payload)
    assert result.candidate.responses[0].retrieved_source_ids == response["retrieved_source_ids"]


def test_duplicate_retrieval_ids_are_rejected(payload):
    payload["candidate"]["responses"][0]["retrieved_source_ids"] = ["same", "same"]
    with pytest.raises(ValidationError, match="duplicate retrieved source IDs"):
        validate(payload)


def test_dataset_references_exist_in_fictional_sources(payload):
    dataset = Dataset.model_validate_json(json.dumps(payload["dataset"]))
    sources = json.loads((ROOT / "datasets/support_policy/v1/sources.json").read_text())
    assert all(source in sources for case in dataset.cases for source in case.relevant_source_ids)
