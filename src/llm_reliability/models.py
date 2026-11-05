"""Data contracts only: scoring and CLI execution are intentionally absent."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Contract(BaseModel):
    # Reject misspelled fields and coercions that could hide malformed fixtures.
    model_config = ConfigDict(extra="forbid", strict=True)


class Criticality(StrEnum):
    STANDARD = "standard"
    CRITICAL = "critical"


def require_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"duplicate {label}: {sorted(duplicates)}")


class EvaluationCase(Contract):
    case_id: Identifier
    question: Identifier
    required_facts: list[Identifier] = Field(min_length=1)
    relevant_source_ids: list[Identifier] = Field(min_length=1)
    criticality: Criticality

    @model_validator(mode="after")
    def unique_assertions(self) -> Self:
        require_unique(self.required_facts, "required facts")
        require_unique(self.relevant_source_ids, "relevant source IDs")
        return self


class Dataset(Contract):
    schema_version: Annotated[int, Field(ge=1, le=1)] = 1
    dataset_id: Identifier
    dataset_version: Identifier
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cases(self) -> Self:
        require_unique([case.case_id for case in self.cases], "dataset case IDs")
        return self


class Configuration(Contract):
    configuration_id: Identifier
    configuration_version: Identifier
    model_version: Identifier
    prompt_version: Identifier
    retrieval_version: Identifier


class RecordedResponse(Contract):
    case_id: Identifier
    answer: str  # Empty answers are valid observations for the future scorer.
    cited_source_ids: list[Identifier]
    retrieved_source_ids: list[Identifier]  # Ordered by rank, highest first.

    @model_validator(mode="after")
    def unique_sources(self) -> Self:
        require_unique(self.cited_source_ids, "cited source IDs")
        require_unique(self.retrieved_source_ids, "retrieved source IDs")
        return self


class Recording(Contract):
    schema_version: Annotated[int, Field(ge=1, le=1)] = 1
    recording_id: Identifier
    dataset_id: Identifier
    dataset_version: Identifier
    configuration: Configuration
    responses: list[RecordedResponse] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cases(self) -> Self:
        require_unique([response.case_id for response in self.responses], "response case IDs")
        return self


class ComparisonInput(Contract):
    dataset: Dataset
    baseline: Recording
    candidate: Recording

    @model_validator(mode="after")
    def compatible_recordings(self) -> Self:
        expected = {case.case_id for case in self.dataset.cases}
        for role, recording in (("baseline", self.baseline), ("candidate", self.candidate)):
            if (recording.dataset_id, recording.dataset_version) != (
                self.dataset.dataset_id, self.dataset.dataset_version
            ):
                raise ValueError(f"{role}: incompatible dataset identity or version")
            actual = {response.case_id for response in recording.responses}
            if actual != expected:
                raise ValueError(
                    f"{role}: case coverage mismatch; missing={sorted(expected - actual)}, "
                    f"unexpected={sorted(actual - expected)}"
                )
        return self
