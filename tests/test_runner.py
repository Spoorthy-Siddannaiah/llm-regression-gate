from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_reliability.loading import load_comparison
from llm_reliability.models import Criticality
from llm_reliability.runner import EvaluationSettings, evaluate_comparison


@pytest.fixture
def inputs():
    root = Path(__file__).resolve().parents[1]
    return load_comparison(
        root / "datasets/support_policy/v1/dataset.json",
        root / "recordings/baseline.synthetic.v1.json",
        root / "recordings/candidate.synthetic.v2.json",
    )


def test_runner_combines_checks_and_preserves_versions(inputs):
    result = evaluate_comparison(inputs, settings=EvaluationSettings(retrieval_k=1))
    assert result.dataset_id == inputs.dataset.dataset_id
    assert result.dataset_version == inputs.dataset.dataset_version
    assert result.dataset_schema_version == 1
    assert result.settings.evaluator_version == "deterministic-v1"
    assert result.settings.retrieval_k == 1
    assert result.baseline.recording_id == inputs.baseline.recording_id
    assert result.candidate.configuration == inputs.candidate.configuration
    assert all(case.all_required_facts_present for case in result.baseline.cases)
    refund, hours = result.candidate.cases
    assert refund.case_id == "refund-window"
    assert refund.criticality == Criticality.CRITICAL
    assert refund.required_facts.missing_facts == ("30 days", "proof of purchase")
    assert not refund.all_required_facts_present
    assert hours.all_required_facts_present
    assert refund.citations.missing_relevant_source_ids == ()
    assert refund.retrieval_recall_at_k == 1.0


def test_alignment_uses_ids_not_recording_order(inputs):
    original = evaluate_comparison(inputs)
    # Reordering preserves coverage; the runner must not pair responses by position.
    reordered = inputs.model_copy(deep=True)
    reordered.candidate.responses.reverse()
    assert evaluate_comparison(reordered) == original


def test_same_settings_change_cutoff_for_both_sides(inputs):
    for recording in (inputs.baseline, inputs.candidate):
        recording.responses[0].retrieved_source_ids.insert(0, "distractor")
    top_one = evaluate_comparison(inputs, settings=EvaluationSettings(retrieval_k=1))
    top_two = evaluate_comparison(inputs, settings=EvaluationSettings(retrieval_k=2))
    for side in ("baseline", "candidate"):
        assert getattr(top_one, side).cases[0].retrieval_recall_at_k == 0.0
        assert getattr(top_two, side).cases[0].retrieval_recall_at_k == 1.0


def test_results_are_repeatable_and_inputs_unchanged(inputs):
    before = inputs.model_dump_json()
    first = evaluate_comparison(inputs)
    second = evaluate_comparison(inputs)
    assert first.model_dump_json() == second.model_dump_json()
    assert inputs.model_dump_json() == before
    payload = first.model_dump(mode="json")
    assert payload["candidate"]["cases"][0]["retrieval_recall_at_k"] == 1.0
    assert payload["candidate"]["cases"][0]["all_required_facts_present"] is False


def test_results_do_not_share_mutable_configuration_or_settings(inputs):
    settings = EvaluationSettings()
    result = evaluate_comparison(inputs, settings=settings)
    inputs.baseline.configuration.prompt_version = "later-edit"
    settings.retrieval_k = 10
    assert result.baseline.configuration.prompt_version == "synthetic-v1"
    assert result.settings.retrieval_k == 3


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "3"])
def test_invalid_k_is_rejected(value):
    with pytest.raises(ValidationError):
        EvaluationSettings(retrieval_k=value)


def test_unknown_evaluator_version_is_rejected():
    with pytest.raises(ValidationError):
        EvaluationSettings(evaluator_version="unknown")
