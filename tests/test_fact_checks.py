from pathlib import Path

import pytest

from llm_reliability.fact_checks import check_required_facts
from llm_reliability.loading import load_comparison
from llm_reliability.models import Criticality, EvaluationCase, RecordedResponse


@pytest.fixture
def case():
    return EvaluationCase(
        case_id="refund-window",
        question="What are the refund requirements?",
        required_facts=["30 days", "proof of purchase"],
        relevant_source_ids=["refund-policy-v1"],
        criticality=Criticality.CRITICAL,
    )


def response(answer, case_id="refund-window"):
    return RecordedResponse(
        case_id=case_id, answer=answer, cited_source_ids=[], retrieved_source_ids=[]
    )


@pytest.mark.parametrize(
    ("answer", "matched", "missing"),
    [
        ("Within 30 days with proof of purchase.", ["30 days", "proof of purchase"], []),
        ("30 DAYS; PROOF\n OF\t PURCHASE", ["30 days", "proof of purchase"], []),
        ("(30 days), with proof of purchase!", ["30 days", "proof of purchase"], []),
        ("Within 60 days.", [], ["30 days", "proof of purchase"]),
        ("Within 30 days.", ["30 days"], ["proof of purchase"]),
        ("", [], ["30 days", "proof of purchase"]),
        (" \n\t", [], ["30 days", "proof of purchase"]),
        ("130 days or 30 dayslong", [], ["30 days", "proof of purchase"]),
        ("30 days, 30 days", ["30 days"], ["proof of purchase"]),
    ],
)
def test_presence_checks(case, answer, matched, missing):
    result = check_required_facts(case, response(answer))
    assert result.case_id == case.case_id
    assert result.matched_facts == tuple(matched)
    assert result.missing_facts == tuple(missing)
    assert result.all_required_facts_present == (not missing)


def test_mismatched_case_is_an_input_error(case):
    with pytest.raises(ValueError, match="expected 'refund-window', received 'other'"):
        check_required_facts(case, response("30 days", case_id="other"))


def test_negated_phrases_still_match_documented_limitation(case):
    result = check_required_facts(
        case, response("The limit is not 30 days. No proof of purchase is required.")
    )
    assert result.all_required_facts_present


def test_paraphrases_do_not_match_documented_limitation(case):
    result = check_required_facts(case, response("Within thirty days; bring your receipt."))
    assert result.missing_facts == tuple(case.required_facts)


def test_punctuation_is_literal_and_regex_characters_are_escaped(case):
    case = case.model_copy(update={"required_facts": ["fee: $5.00 (USD)"]})
    assert check_required_facts(case, response("The fee: $5.00 (USD).")).all_required_facts_present
    assert not check_required_facts(case, response("fee: $5x00 (USD)")).all_required_facts_present


def test_synthetic_recordings_expose_missing_candidate_facts_without_mutation():
    root = Path(__file__).resolve().parents[1]
    comparison = load_comparison(
        root / "datasets/support_policy/v1/dataset.json",
        root / "recordings/baseline.synthetic.v1.json",
        root / "recordings/candidate.synthetic.v2.json",
    )
    original = comparison.model_dump_json()
    baseline = {item.case_id: item for item in comparison.baseline.responses}
    candidate = {item.case_id: item for item in comparison.candidate.responses}
    for case in comparison.dataset.cases:
        assert check_required_facts(case, baseline[case.case_id]).all_required_facts_present
        result = check_required_facts(case, candidate[case.case_id])
        if case.case_id == "refund-window":
            assert result.missing_facts == ("30 days", "proof of purchase")
        else:
            assert result.all_required_facts_present
    assert comparison.model_dump_json() == original
