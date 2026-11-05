"""Narrow phrase-presence assertions, not semantic correctness judgments."""

import re

from llm_reliability.models import Contract, EvaluationCase, Identifier, RecordedResponse


class RequiredFactResult(Contract):
    case_id: Identifier
    matched_facts: tuple[str, ...]
    missing_facts: tuple[str, ...]

    @property
    def all_required_facts_present(self) -> bool:
        return not self.missing_facts


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def check_required_facts(
    case: EvaluationCase, response: RecordedResponse
) -> RequiredFactResult:
    """Check normalized literal phrases with boundaries at either end.

    This does not understand negation, contradictions, or paraphrases. A passing
    result says only that each required phrase occurs, not that the answer is true.
    """
    if case.case_id != response.case_id:
        raise ValueError(
            f"case ID mismatch: expected {case.case_id!r}, received {response.case_id!r}"
        )

    answer = _normalize(response.answer)
    matched: list[str] = []
    missing: list[str] = []
    for fact in case.required_facts:
        # Avoid matching '30 days' inside '130 days' or '30 dayslong'.
        pattern = rf"(?<!\w){re.escape(_normalize(fact))}(?!\w)"
        destination = matched if re.search(pattern, answer) else missing
        destination.append(fact)

    return RequiredFactResult(
        case_id=case.case_id,
        matched_facts=tuple(matched),
        missing_facts=tuple(missing),
    )
