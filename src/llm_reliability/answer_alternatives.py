"""Separate OR-of-phrases diagnostic; does not change deterministic-v1 gates."""

import re
from typing import Literal, Self

from pydantic import Field, TypeAdapter, computed_field, model_validator

from llm_reliability.models import Contract, Identifier, RecordedResponse, require_unique


_REFERENCE_ANSWERS = TypeAdapter(list[Identifier], config={"strict": True})


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


class AnswerAlternatives(Contract):
    case_id: Identifier
    alternatives: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_normalized_variants(self) -> Self:
        require_unique([_normalized(value) for value in self.alternatives], "normalized answer alternatives")
        return self


class AlternativeAnswerResult(Contract):
    evaluator_version: Literal["alternative-phrases-v1"] = "alternative-phrases-v1"
    case_id: Identifier
    matched_alternatives: tuple[str, ...]
    unmatched_alternatives: tuple[str, ...]

    @computed_field
    @property
    def any_alternative_present(self) -> bool:
        return bool(self.matched_alternatives)


def from_reference_answers(case_id: str, answers: list[str]) -> AnswerAlternatives:
    """Deduplicate repeated upstream annotations; never invent or split aliases."""
    # Validate before deduplication so blank/malformed annotations remain errors.
    validated = _REFERENCE_ANSWERS.validate_python(answers)
    unique = {}
    for value in validated:
        unique.setdefault(_normalized(value), value)
    return AnswerAlternatives(case_id=case_id, alternatives=list(unique.values()))


def check_answer_alternatives(
    expectation: AnswerAlternatives, response: RecordedResponse,
) -> AlternativeAnswerResult:
    if expectation.case_id != response.case_id:
        raise ValueError(
            f"case ID mismatch: expected {expectation.case_id!r}, received {response.case_id!r}"
        )
    answer = _normalized(response.answer)
    matched, unmatched = [], []
    for variant in expectation.alternatives:
        pattern = rf"(?<!\w){re.escape(_normalized(variant))}(?!\w)"
        (matched if re.search(pattern, answer) else unmatched).append(variant)
    return AlternativeAnswerResult(
        case_id=expectation.case_id, matched_alternatives=tuple(matched),
        unmatched_alternatives=tuple(unmatched),
    )
