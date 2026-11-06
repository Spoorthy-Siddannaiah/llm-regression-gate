from pathlib import Path

import pytest

from llm_reliability.loading import load_comparison
from llm_reliability.models import Criticality, EvaluationCase, RecordedResponse
from llm_reliability.source_checks import check_citation_ids, check_retrieval_recall


@pytest.fixture
def case():
    return EvaluationCase(
        case_id="example", question="Question?", required_facts=["fact"],
        relevant_source_ids=["a", "b"], criticality=Criticality.STANDARD,
    )


def response(*, cited=(), retrieved=(), case_id="example"):
    return RecordedResponse(
        case_id=case_id, answer="", cited_source_ids=list(cited),
        retrieved_source_ids=list(retrieved),
    )


def test_citations_are_partitioned_by_labels_without_claiming_support(case):
    result = check_citation_ids(case, response(cited=["b", "unlabelled"]))
    assert result.relevant_cited_source_ids == ("b",)
    assert result.unlabelled_cited_source_ids == ("unlabelled",)
    assert result.missing_relevant_source_ids == ("a",)


def test_no_citations_reports_all_missing(case):
    result = check_citation_ids(case, response())
    assert result.relevant_cited_source_ids == ()
    assert result.unlabelled_cited_source_ids == ()
    assert result.missing_relevant_source_ids == ("a", "b")


def test_all_relevant_citations(case):
    result = check_citation_ids(case, response(cited=["b", "a"]))
    assert result.relevant_cited_source_ids == ("b", "a")
    assert result.missing_relevant_source_ids == ()


@pytest.mark.parametrize(
    ("retrieved", "k", "found", "missing", "recall"),
    [
        (["other", "a", "b"], 1, (), ("a", "b"), 0.0),
        (["other", "a", "b"], 2, ("a",), ("b",), 0.5),
        (["other", "a", "b"], 3, ("a", "b"), (), 1.0),
        (["a"], 10, ("a",), ("b",), 0.5),
        ([], 3, (), ("a", "b"), 0.0),
    ],
)
def test_recall_uses_rank_cutoff_and_relevant_count(case, retrieved, k, found, missing, recall):
    item = response(retrieved=retrieved)
    before = item.model_dump_json()
    result = check_retrieval_recall(case, item, k=k)
    assert result.retrieved_source_ids_at_k == tuple(retrieved[:k])
    assert result.found_relevant_source_ids == found
    assert result.missing_relevant_source_ids == missing
    assert result.recall_at_k == recall
    assert item.model_dump_json() == before


@pytest.mark.parametrize("k", [0, -1, True, 1.5, "2", None])
def test_invalid_k_is_rejected(case, k):
    with pytest.raises(ValueError, match="positive integer"):
        check_retrieval_recall(case, response(), k=k)


def test_case_mismatch_rejected_by_both_checks(case):
    with pytest.raises(ValueError, match="case ID mismatch"):
        check_citation_ids(case, response(case_id="other"))
    with pytest.raises(ValueError, match="case ID mismatch"):
        check_retrieval_recall(case, response(case_id="other"), k=1)


def test_synthetic_candidate_can_have_good_sources_and_bad_answer():
    root = Path(__file__).resolve().parents[1]
    comparison = load_comparison(
        root / "datasets/support_policy/v1/dataset.json",
        root / "recordings/baseline.synthetic.v1.json",
        root / "recordings/candidate.synthetic.v2.json",
    )
    before = comparison.model_dump_json()
    for recording in (comparison.baseline, comparison.candidate):
        by_id = {item.case_id: item for item in recording.responses}
        for case in comparison.dataset.cases:
            item = by_id[case.case_id]
            assert check_citation_ids(case, item).missing_relevant_source_ids == ()
            assert check_retrieval_recall(case, item, k=1).recall_at_k == 1.0
    assert comparison.model_dump_json() == before
