"""Citation membership in the supplied corpus, not relevance or semantic support."""

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, computed_field, model_validator

from llm_reliability.models import ComparisonInput, Contract, Identifier, RecordedResponse, require_unique
from llm_reliability.retrieval import SourceCorpus


class CitationExistenceResult(Contract):
    case_id: Identifier
    existing_source_ids: tuple[str, ...]
    unknown_source_ids: tuple[str, ...]

    @model_validator(mode="after")
    def unique_partition(self) -> Self:
        require_unique(list(self.existing_source_ids + self.unknown_source_ids), "citation existence IDs")
        return self

    @computed_field
    @property
    def has_citations(self) -> bool:
        return bool(self.existing_source_ids or self.unknown_source_ids)

    @computed_field
    @property
    def all_cited_ids_exist(self) -> bool | None:
        # No citation is an absence of evidence, not a successful citation check.
        return not self.unknown_source_ids if self.has_citations else None


def check_citation_existence(response: RecordedResponse, corpus: SourceCorpus) -> CitationExistenceResult:
    return CitationExistenceResult(
        case_id=response.case_id,
        existing_source_ids=tuple(source for source in response.cited_source_ids if source in corpus.root),
        unknown_source_ids=tuple(source for source in response.cited_source_ids if source not in corpus.root),
    )


class CitationExistenceSummary(Contract):
    recording_id: Identifier
    cases: tuple[CitationExistenceResult, ...] = Field(min_length=1)

    @computed_field
    @property
    def unknown_citation_count(self) -> int:
        return sum(len(case.unknown_source_ids) for case in self.cases)

    @computed_field
    @property
    def cases_without_citations(self) -> int:
        return sum(not case.has_citations for case in self.cases)

    @computed_field
    @property
    def existing_citation_count(self) -> int:
        return sum(len(case.existing_source_ids) for case in self.cases)


class CitationExistenceDiagnostic(Contract):
    evaluator_version: Literal["citation-existence-v1"] = "citation-existence-v1"
    corpus_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    source_count: int = Field(gt=0)
    baseline: CitationExistenceSummary
    candidate: CitationExistenceSummary


def build_citation_existence(
    inputs: ComparisonInput, corpus: SourceCorpus, *, corpus_sha256: str,
) -> CitationExistenceDiagnostic:
    summaries = {}
    for role, recording in (("baseline", inputs.baseline), ("candidate", inputs.candidate)):
        by_id = {response.case_id: response for response in recording.responses}
        summaries[role] = CitationExistenceSummary(
            recording_id=recording.recording_id,
            cases=tuple(check_citation_existence(by_id[case.case_id], corpus) for case in inputs.dataset.cases),
        )
    return CitationExistenceDiagnostic(
        corpus_sha256=corpus_sha256, source_count=len(corpus.root), **summaries,
    )
