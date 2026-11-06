from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_reliability.gates import GatePolicy, MetricThreshold, compare_and_gate
from llm_reliability.loading import load_comparison


@pytest.fixture
def inputs():
    root = Path(__file__).resolve().parents[1]
    return load_comparison(
        root / "datasets/support_policy/v1/dataset.json",
        root / "recordings/baseline.synthetic.v1.json",
        root / "recordings/candidate.synthetic.v2.json",
    )


def make_candidate_identical(inputs):
    inputs.candidate.responses = [item.model_copy(deep=True) for item in inputs.baseline.responses]


def test_intentional_critical_regression_fails_with_evidence(inputs):
    before = inputs.model_dump_json()
    result = compare_and_gate(inputs)
    assert not result.passed
    facts, citations, recall = result.metrics
    assert (facts.baseline, facts.candidate, facts.delta) == (1.0, 0.5, -0.5)
    assert citations.delta == recall.delta == 0.0
    critical = next(f for f in result.failures if f.code == "critical_facts_missing")
    assert critical.case_id == "refund-window"
    assert "30 days" in critical.message
    assert "proof of purchase" in critical.message
    assert inputs.model_dump_json() == before
    assert result.model_dump(mode="json")["passed"] is False


def test_unchanged_candidate_passes(inputs):
    make_candidate_identical(inputs)
    result = compare_and_gate(inputs)
    assert result.passed
    assert result.failures == ()


def test_improved_candidate_passes(inputs):
    inputs.baseline.responses[0].answer = ""
    make_candidate_identical(inputs)
    inputs.candidate.responses[0].answer = "30 days with proof of purchase"
    result = compare_and_gate(inputs)
    assert result.passed
    assert result.metrics[0].delta == 0.5


def test_critical_failure_cannot_hide_behind_permitted_average_drop(inputs):
    policy = GatePolicy(fact_coverage=MetricThreshold(max_drop=1.0))
    result = compare_and_gate(inputs, policy=policy)
    assert [f.code for f in result.failures] == ["critical_facts_missing"]


def test_already_bad_critical_baseline_does_not_excuse_candidate(inputs):
    inputs.baseline.responses[0].answer = inputs.candidate.responses[0].answer
    result = compare_and_gate(inputs)
    assert result.metrics[0].delta == 0.0
    assert not result.passed
    assert [f.code for f in result.failures] == ["critical_facts_missing"]


def test_absolute_floor_catches_unchanged_poor_standard_case(inputs):
    make_candidate_identical(inputs)
    for recording in (inputs.baseline, inputs.candidate):
        recording.responses[1].answer = ""
    result = compare_and_gate(inputs, policy=GatePolicy(fact_coverage=MetricThreshold(minimum=0.8)))
    assert [f.code for f in result.failures] == ["below_minimum"]


@pytest.mark.parametrize("drop, passes", [(0.5, True), (0.49, False), (0.51, True)])
def test_drop_boundary_is_inclusive(inputs, drop, passes):
    result = compare_and_gate(inputs, policy=GatePolicy(
        require_critical_facts=False, fact_coverage=MetricThreshold(max_drop=drop),
    ))
    assert result.passed == passes


@pytest.mark.parametrize("minimum, passes", [(0.5, True), (0.51, False), (0.49, True)])
def test_floor_boundary_is_inclusive(inputs, minimum, passes):
    result = compare_and_gate(inputs, policy=GatePolicy(
        require_critical_facts=False,
        fact_coverage=MetricThreshold(minimum=minimum, max_drop=1.0),
    ))
    assert result.passed == passes


@pytest.mark.parametrize("field, metric", [
    ("cited_source_ids", "citation_label_coverage"),
    ("retrieved_source_ids", "retrieval_recall"),
])
def test_source_metric_regressions_are_detected(inputs, field, metric):
    make_candidate_identical(inputs)
    setattr(inputs.candidate.responses[0], field, [])
    result = compare_and_gate(inputs)
    assert not result.passed
    assert [(f.code, f.metric) for f in result.failures] == [("excessive_drop", metric)]


@pytest.mark.parametrize("field", ["minimum", "max_drop"])
@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_invalid_thresholds_rejected(field, value):
    with pytest.raises(ValidationError):
        MetricThreshold(**{field: value})


def test_policy_is_snapshotted_and_results_repeatable(inputs):
    policy = GatePolicy()
    result = compare_and_gate(inputs, policy=policy)
    assert result.model_dump_json() == compare_and_gate(inputs, policy=policy).model_dump_json()
    policy.fact_coverage.max_drop = 1.0
    assert result.policy.fact_coverage.max_drop == 0.0
