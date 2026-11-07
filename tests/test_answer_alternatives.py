import pytest
from pydantic import ValidationError

from llm_reliability.answer_alternatives import (
    AnswerAlternatives, check_answer_alternatives, from_reference_answers,
)
from llm_reliability.fact_checks import check_required_facts
from llm_reliability.models import Criticality, EvaluationCase, RecordedResponse


def response(answer, case_id="example"):
    return RecordedResponse(case_id=case_id, answer=answer, cited_source_ids=[], retrieved_source_ids=[])


@pytest.mark.parametrize("answer, matched", [
    ("Norseman", ("Norseman",)), ("VIKING!", ("Viking",)),
    ("Norseman, Viking", ("Norseman", "Viking")), ("", ()), ("Vikinglike", ()),
])
def test_any_variant_can_satisfy_the_expectation(answer, matched):
    expectation = AnswerAlternatives(case_id="example", alternatives=["Norseman", "Viking"])
    result = check_answer_alternatives(expectation, response(answer))
    assert result.matched_alternatives == matched
    assert result.any_alternative_present == bool(matched)
    assert result.model_dump()["evaluator_version"] == "alternative-phrases-v1"


def test_required_facts_still_use_and_while_alternatives_use_or():
    case = EvaluationCase(
        case_id="example", question="Meaning?", required_facts=["Norseman", "Viking"],
        relevant_source_ids=["source"], criticality=Criticality.STANDARD,
    )
    observation = response("Norseman")
    assert check_required_facts(case, observation).missing_facts == ("Viking",)
    assert check_answer_alternatives(
        AnswerAlternatives(case_id="example", alternatives=case.required_facts), observation,
    ).any_alternative_present


@pytest.mark.parametrize("variants", [[], [" "], ["Viking", " VIKING "], ["30 days", "30\n days"]])
def test_empty_or_duplicate_authored_variants_rejected(variants):
    with pytest.raises(ValidationError):
        AnswerAlternatives(case_id="example", alternatives=variants)


def test_repeated_reference_annotations_are_deduplicated_without_splitting():
    result = from_reference_answers("example", ["Norseman, Viking", "Norseman, Viking", " VIKING "])
    assert result.alternatives == ["Norseman, Viking", "VIKING"]


@pytest.mark.parametrize("variants", [[], [""], [1], "Viking"])
def test_malformed_reference_annotations_are_not_silently_removed(variants):
    with pytest.raises(ValidationError):
        from_reference_answers("example", variants)


def test_case_mismatch_is_an_input_error():
    with pytest.raises(ValueError, match="case ID mismatch"):
        check_answer_alternatives(AnswerAlternatives(case_id="example", alternatives=["yes"]), response("yes", "other"))


def test_negation_and_unit_conversion_remain_documented_limits():
    expectation = AnswerAlternatives(case_id="example", alternatives=["15 kilometres"])
    assert check_answer_alternatives(expectation, response("Not 15 kilometres")).any_alternative_present
    assert not check_answer_alternatives(expectation, response("9 miles")).any_alternative_present


def test_whitespace_literal_punctuation_and_repeatability():
    expectation = AnswerAlternatives(case_id="example", alternatives=["fee: $5.00 (USD)"])
    observation = response("FEE:\t$5.00 (USD)")
    before = expectation.model_dump_json(), observation.model_dump_json()
    assert check_answer_alternatives(expectation, observation).any_alternative_present
    assert not check_answer_alternatives(expectation, response("fee: $5x00 (USD)")).any_alternative_present
    assert check_answer_alternatives(expectation, observation) == check_answer_alternatives(expectation, observation)
    assert before == (expectation.model_dump_json(), observation.model_dump_json())
