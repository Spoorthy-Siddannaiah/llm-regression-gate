"""Deterministic comparison policy; no reports, process exits, or baseline writes."""

from typing import Literal

from pydantic import Field, computed_field

from llm_reliability.models import ComparisonInput, Contract, Criticality, Identifier
from llm_reliability.runner import (
    ComparisonEvaluation, EvaluationSettings, RecordingEvaluation, evaluate_comparison,
)


class MetricThreshold(Contract):
    minimum: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    max_drop: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)


class GatePolicy(Contract):
    policy_version: Literal["deterministic-gate-v1"] = "deterministic-gate-v1"
    require_critical_facts: bool = True
    fact_coverage: MetricThreshold = Field(default_factory=MetricThreshold)
    citation_label_coverage: MetricThreshold = Field(default_factory=MetricThreshold)
    retrieval_recall: MetricThreshold = Field(default_factory=MetricThreshold)


class MetricComparison(Contract):
    metric: Literal["fact_coverage", "citation_label_coverage", "retrieval_recall"]
    baseline: float
    candidate: float

    @computed_field
    @property
    def delta(self) -> float:
        """Candidate minus baseline; negative values indicate a drop."""
        return self.candidate - self.baseline


class GateFailure(Contract):
    code: Literal["critical_facts_missing", "below_minimum", "excessive_drop"]
    metric: str
    case_id: Identifier | None = None
    message: str


class GateResult(Contract):
    evaluation: ComparisonEvaluation
    policy: GatePolicy
    metrics: tuple[MetricComparison, ...]
    failures: tuple[GateFailure, ...]

    @computed_field
    @property
    def passed(self) -> bool:
        return not self.failures


def _means(recording: RecordingEvaluation) -> dict[str, float]:
    # The input contracts guarantee nonempty cases and nonempty relevance/fact labels.
    fact_coverage = []
    citation_coverage = []
    recall = []
    for case in recording.cases:
        matched = len(case.required_facts.matched_facts)
        fact_coverage.append(matched / (matched + len(case.required_facts.missing_facts)))
        cited = len(case.citations.relevant_cited_source_ids)
        citation_coverage.append(cited / (cited + len(case.citations.missing_relevant_source_ids)))
        recall.append(case.retrieval_recall_at_k)
    return {
        "fact_coverage": sum(fact_coverage) / len(fact_coverage),
        "citation_label_coverage": sum(citation_coverage) / len(citation_coverage),
        "retrieval_recall": sum(recall) / len(recall),
    }


def compare_and_gate(
    inputs: ComparisonInput, *, settings: EvaluationSettings | None = None,
    policy: GatePolicy | None = None,
) -> GateResult:
    """Evaluate compatible inputs together so settings cannot differ between sides.

    Means weight cases equally. Thresholds use absolute 0..1 differences, not
    relative percentages. Equality passes; a 1e-12 tolerance absorbs float noise.
    """
    selected = policy if policy is not None else GatePolicy()
    evaluation = evaluate_comparison(inputs, settings=settings)
    baseline = _means(evaluation.baseline)
    candidate = _means(evaluation.candidate)
    comparisons = []
    failures = []
    for name in ("fact_coverage", "citation_label_coverage", "retrieval_recall"):
        metric = MetricComparison(metric=name, baseline=baseline[name], candidate=candidate[name])
        comparisons.append(metric)
        threshold = getattr(selected, name)
        if threshold.minimum - metric.candidate > 1e-12:
            failures.append(GateFailure(
                code="below_minimum", metric=name,
                message=f"{name}: candidate {metric.candidate:.6f} below minimum {threshold.minimum:.6f}",
            ))
        if -metric.delta - threshold.max_drop > 1e-12:
            failures.append(GateFailure(
                code="excessive_drop", metric=name,
                message=f"{name}: drop {-metric.delta:.6f} exceeds allowed {threshold.max_drop:.6f}",
            ))
    if selected.require_critical_facts:
        for case in evaluation.candidate.cases:
            if case.criticality == Criticality.CRITICAL and case.required_facts.missing_facts:
                failures.append(GateFailure(
                    code="critical_facts_missing", metric="fact_coverage", case_id=case.case_id,
                    message=f"{case.case_id}: missing required phrases {case.required_facts.missing_facts!r}",
                ))
    return GateResult(
        evaluation=evaluation, policy=selected.model_copy(deep=True),
        metrics=tuple(comparisons), failures=tuple(failures),
    )
