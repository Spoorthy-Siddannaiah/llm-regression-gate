"""Evaluate validated recordings; no gate decisions, file writes, or live calls."""

from typing import Literal

from pydantic import Field, computed_field

from llm_reliability.fact_checks import RequiredFactResult, check_required_facts
from llm_reliability.models import (
    ComparisonInput, Configuration, Contract, Criticality, Dataset, Identifier, Recording,
)
from llm_reliability.source_checks import (
    CitationResult, RetrievalRecallResult, check_citation_ids, check_retrieval_recall,
)


class EvaluationSettings(Contract):
    evaluator_version: Literal["deterministic-v1"] = "deterministic-v1"
    retrieval_k: int = Field(default=3, gt=0)


class CaseEvaluation(Contract):
    case_id: Identifier
    criticality: Criticality
    required_facts: RequiredFactResult
    citations: CitationResult
    retrieval: RetrievalRecallResult

    @computed_field
    @property
    def all_required_facts_present(self) -> bool:
        return self.required_facts.all_required_facts_present

    @computed_field
    @property
    def retrieval_recall_at_k(self) -> float:
        return self.retrieval.recall_at_k


class RecordingEvaluation(Contract):
    recording_id: Identifier
    configuration: Configuration
    cases: tuple[CaseEvaluation, ...]


class ComparisonEvaluation(Contract):
    dataset_id: Identifier
    dataset_version: Identifier
    dataset_schema_version: int
    settings: EvaluationSettings
    baseline: RecordingEvaluation
    candidate: RecordingEvaluation


def _evaluate_recording(
    dataset: Dataset, recording: Recording, settings: EvaluationSettings
) -> RecordingEvaluation:
    # ComparisonInput already guarantees exact coverage and unique IDs.
    by_id = {response.case_id: response for response in recording.responses}
    cases = tuple(
        CaseEvaluation(
            case_id=case.case_id,
            criticality=case.criticality,
            required_facts=check_required_facts(case, by_id[case.case_id]),
            citations=check_citation_ids(case, by_id[case.case_id]),
            retrieval=check_retrieval_recall(
                case, by_id[case.case_id], k=settings.retrieval_k
            ),
        )
        for case in dataset.cases
    )
    return RecordingEvaluation(
        recording_id=recording.recording_id,
        configuration=recording.configuration.model_copy(deep=True),
        cases=cases,
    )


def evaluate_comparison(
    inputs: ComparisonInput, *, settings: EvaluationSettings | None = None
) -> ComparisonEvaluation:
    """Apply identical settings to both recordings of a validated comparison.

    Inputs follow the model contract: do not mutate validated models in place.
    Results snapshot configuration/settings so later caller edits cannot alter them.
    Version labels are manually maintained; they do not establish content identity.
    """
    selected = settings if settings is not None else EvaluationSettings()
    return ComparisonEvaluation(
        dataset_id=inputs.dataset.dataset_id,
        dataset_version=inputs.dataset.dataset_version,
        dataset_schema_version=inputs.dataset.schema_version,
        settings=selected.model_copy(deep=True),
        baseline=_evaluate_recording(inputs.dataset, inputs.baseline, selected),
        candidate=_evaluate_recording(inputs.dataset, inputs.candidate, selected),
    )
