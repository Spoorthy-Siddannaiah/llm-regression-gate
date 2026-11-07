"""Typed, offline answer-variant evidence reusable by scripts and reports."""

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field, RootModel, computed_field

from llm_reliability.answer_alternatives import (
    AlternativeAnswerResult, check_answer_alternatives, from_reference_answers,
)
from llm_reliability.fact_checks import check_required_facts
from llm_reliability.loading import load_comparison, load_corpus
from llm_reliability.models import Contract, Identifier


class ReferenceAnswer(Contract):
    answer_start: int = Field(ge=0)
    text: Identifier


class Reference(Contract):
    upstream_question_id: Identifier
    article_title: Identifier
    source_id: Identifier
    answers: list[ReferenceAnswer] = Field(min_length=1)


class References(RootModel[dict[str, Reference]]):
    pass


class DiagnosticCase(Contract):
    case_id: Identifier
    alternatives: list[Identifier]
    required_facts_present_v1: bool
    alternative_result: AlternativeAnswerResult


class DiagnosticSummary(Contract):
    recording_id: Identifier
    cases: list[DiagnosticCase] = Field(min_length=1)

    @computed_field
    @property
    def required_fact_case_coverage_v1(self) -> float:
        return sum(case.required_facts_present_v1 for case in self.cases) / len(self.cases)

    @computed_field
    @property
    def alternative_case_coverage(self) -> float:
        return sum(case.alternative_result.any_alternative_present for case in self.cases) / len(self.cases)


class DiagnosticRoles(Contract):
    baseline: DiagnosticSummary
    candidate: DiagnosticSummary


class AlternativesDiagnostic(Contract):
    artifact_kind: Literal["alternative_answer_diagnostic"] = "alternative_answer_diagnostic"
    schema_version: Literal[1] = 1
    evaluator_version: Literal["alternative-phrases-v1"] = "alternative-phrases-v1"
    case_count: int = Field(gt=0)
    input_sha256: dict[str, str]
    results: DiagnosticRoles
    limits: str = "OR of literal annotated phrases only, not semantic correctness. No invented aliases, unit conversion, negation handling, gate changes, or baseline promotion."


def build_diagnostic(
    dataset: Path, sources: Path, references: Path, baseline: Path, candidate: Path,
) -> AlternativesDiagnostic:
    inputs = load_comparison(dataset, baseline, candidate, sources_path=sources, require_manifests=True)
    annotations = References.model_validate_json(references.read_text(encoding="utf-8")).root
    corpus = load_corpus(sources).root
    expected_ids = {case.case_id for case in inputs.dataset.cases}
    if set(annotations) != expected_ids:
        raise ValueError(f"reference case coverage mismatch: missing={sorted(expected_ids - annotations.keys())}, unexpected={sorted(annotations.keys() - expected_ids)}")
    summaries = {}
    for role, recording in (("baseline", inputs.baseline), ("candidate", inputs.candidate)):
        responses = {response.case_id: response for response in recording.responses}
        cases = []
        for case in inputs.dataset.cases:
            reference = annotations[case.case_id]
            if reference.source_id not in case.relevant_source_ids:
                raise ValueError(f"{case.case_id}: reference source does not match dataset labels")
            if reference.source_id not in corpus:
                raise ValueError(f"{case.case_id}: reference source absent from corpus")
            context = corpus[reference.source_id]
            for answer in reference.answers:
                if context[answer.answer_start:answer.answer_start + len(answer.text)] != answer.text:
                    raise ValueError(f"{case.case_id}: reference answer span does not match source")
            expectation = from_reference_answers(case.case_id, [answer.text for answer in reference.answers])
            observation = responses[case.case_id]
            cases.append(DiagnosticCase(
                case_id=case.case_id, alternatives=expectation.alternatives,
                required_facts_present_v1=check_required_facts(case, observation).all_required_facts_present,
                alternative_result=check_answer_alternatives(expectation, observation),
            ))
        summaries[role] = DiagnosticSummary(recording_id=recording.recording_id, cases=cases)
    return AlternativesDiagnostic(
        case_count=len(expected_ids), results=DiagnosticRoles(**summaries),
        input_sha256={
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in (("dataset", dataset), ("sources", sources), ("references", references),
                               ("baseline", baseline), ("candidate", candidate))
        },
    )


def evaluate(dataset: Path, sources: Path, references: Path, baseline: Path, candidate: Path) -> dict:
    """Keep the standalone diagnostic's existing JSON output contract."""
    return build_diagnostic(dataset, sources, references, baseline, candidate).model_dump(mode="json")
