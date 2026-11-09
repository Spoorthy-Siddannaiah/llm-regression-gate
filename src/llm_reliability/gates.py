"""Deterministic comparison policy; no reports, process exits, or baseline writes."""

from typing import Annotated, Literal

from pydantic import Field, RootModel, computed_field, model_validator, model_serializer

from llm_reliability.models import ComparisonInput, Contract, Criticality, Identifier
from llm_reliability.citation_existence import CitationExistenceDiagnostic, build_citation_existence
from llm_reliability.retrieval import SourceCorpus
from llm_reliability.runner import (
    CaseEvaluation, ComparisonEvaluation, EvaluationSettings, RecordingEvaluation, evaluate_comparison,
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
    max_regressed_cases: int | None = Field(default=None, ge=0)

    @model_serializer(mode="wrap")
    def serialize_policy(self, handler):
        payload = handler(self)
        if self.max_regressed_cases is None:
            payload.pop("max_regressed_cases", None)
        return payload


class UnknownCitationLimits(Contract):
    max_candidate_unknown: int = Field(default=0, ge=0)
    max_increase: int = Field(default=0, ge=0)


class GatePolicyV2(GatePolicy):
    policy_version: Literal["deterministic-gate-v2"] = "deterministic-gate-v2"
    unknown_citations: UnknownCitationLimits


class GatePolicyDocument(RootModel[Annotated[GatePolicy | GatePolicyV2, Field(discriminator="policy_version")]]):
    @model_validator(mode="before")
    @classmethod
    def legacy_default_version(cls, value: object) -> object:
        # Version omission historically means v1; never silently enable enforcement.
        if isinstance(value, dict) and "policy_version" not in value:
            return {"policy_version": "deterministic-gate-v1", **value}
        return value


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
    code: Literal["critical_facts_missing", "below_minimum", "excessive_drop",
                  "unknown_citation_limit", "unknown_citation_increase", "excessive_case_regressions"]
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


class CitationGateEvidence(Contract):
    diagnostic: CitationExistenceDiagnostic

    @computed_field
    @property
    def baseline_unknown_count(self) -> int:
        return self.diagnostic.baseline.unknown_citation_count

    @computed_field
    @property
    def candidate_unknown_count(self) -> int:
        return self.diagnostic.candidate.unknown_citation_count

    @computed_field
    @property
    def increase(self) -> int:
        return self.candidate_unknown_count - self.baseline_unknown_count


class GateResultV2(GateResult):
    policy: GatePolicyV2
    citation_existence_gate: CitationGateEvidence


class CaseChange(Contract):
    case_id: Identifier
    criticality: Criticality
    metrics: tuple[MetricComparison, ...]

    @computed_field
    @property
    def regressed_metrics(self) -> tuple[str, ...]:
        return tuple(m.metric for m in self.metrics if m.delta < -1e-12)

    @computed_field
    @property
    def improved_metrics(self) -> tuple[str, ...]:
        return tuple(m.metric for m in self.metrics if m.delta > 1e-12)

    @computed_field
    @property
    def status(self) -> str:
        return "regressed" if self.regressed_metrics else "improved" if self.improved_metrics else "unchanged"

    @computed_field
    @property
    def critical_regression(self) -> bool:
        return self.criticality == Criticality.CRITICAL and bool(self.regressed_metrics)


def build_case_changes(evaluation: ComparisonEvaluation) -> tuple[CaseChange, ...]:
    old = {case.case_id: case for case in evaluation.baseline.cases}
    return tuple(CaseChange(
        case_id=case.case_id, criticality=case.criticality,
        metrics=tuple(MetricComparison(metric=name, baseline=_means_case(old[case.case_id])[name],
                                       candidate=value) for name, value in _means_case(case).items()),
    ) for case in evaluation.candidate.cases)


def _means_case(case: CaseEvaluation) -> dict[str, float]:
    matched = len(case.required_facts.matched_facts)
    cited = len(case.citations.relevant_cited_source_ids)
    return {
        "fact_coverage": matched / (matched + len(case.required_facts.missing_facts)),
        "citation_label_coverage": cited / (cited + len(case.citations.missing_relevant_source_ids)),
        "retrieval_recall": case.retrieval_recall_at_k,
    }


def _means(recording: RecordingEvaluation) -> dict[str, float]:
    # The input contracts guarantee nonempty cases and nonempty relevance/fact labels.
    values = [_means_case(case) for case in recording.cases]
    return {name: sum(case[name] for case in values) / len(values) for name in values[0]}


def compare_and_gate(
    inputs: ComparisonInput, *, settings: EvaluationSettings | None = None,
    policy: GatePolicy | GatePolicyV2 | None = None,
    corpus: SourceCorpus | None = None, corpus_sha256: str | None = None,
) -> GateResult:
    """Evaluate compatible inputs together so settings cannot differ between sides.

    Means weight cases equally. Thresholds use absolute 0..1 differences, not
    relative percentages. Equality passes; a 1e-12 tolerance absorbs float noise.
    """
    selected = policy if policy is not None else GatePolicy()
    citation_evidence = None
    if isinstance(selected, GatePolicyV2):
        if corpus is None or corpus_sha256 is None:
            raise ValueError("deterministic-gate-v2 requires corpus and corpus_sha256")
        citation_evidence = CitationGateEvidence(diagnostic=build_citation_existence(
            inputs, corpus, corpus_sha256=corpus_sha256,
        ))
    evaluation = evaluate_comparison(inputs, settings=settings)
    if selected.max_regressed_cases is not None:
        regressed = [change.case_id for change in build_case_changes(evaluation) if change.regressed_metrics]
        if len(regressed) > selected.max_regressed_cases:
            case_failure = GateFailure(code="excessive_case_regressions", metric="regressed_case_count",
                                       message=f"regressed case count {len(regressed)} exceeds maximum {selected.max_regressed_cases}")
        else:
            case_failure = None
    else:
        case_failure = None
    baseline = _means(evaluation.baseline)
    candidate = _means(evaluation.candidate)
    comparisons = []
    failures = [case_failure] if case_failure is not None else []
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
    if isinstance(selected, GatePolicyV2):
        assert citation_evidence is not None
        limits = selected.unknown_citations
        count = citation_evidence.candidate_unknown_count
        increase = citation_evidence.increase
        affected = [case.case_id for case in citation_evidence.diagnostic.candidate.cases if case.unknown_source_ids]
        if count > limits.max_candidate_unknown:
            failures.append(GateFailure(
                code="unknown_citation_limit", metric="unknown_citation_count",
                message=f"candidate unknown citation count {count} exceeds maximum {limits.max_candidate_unknown}; cases={affected}",
            ))
        if increase > limits.max_increase:
            failures.append(GateFailure(
                code="unknown_citation_increase", metric="unknown_citation_count",
                message=f"unknown citation count increase {increase} exceeds allowed {limits.max_increase}; cases={affected}",
            ))
        return GateResultV2(
            evaluation=evaluation, policy=selected.model_copy(deep=True),
            metrics=tuple(comparisons), failures=tuple(failures),
            citation_existence_gate=citation_evidence,
        )
    return GateResult(
        evaluation=evaluation, policy=selected.model_copy(deep=True),
        metrics=tuple(comparisons), failures=tuple(failures),
    )
