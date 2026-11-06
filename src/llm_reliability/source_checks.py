"""Source-ID checks against case labels, not semantic citation support."""

from pydantic import Field

from llm_reliability.models import Contract, EvaluationCase, Identifier, RecordedResponse


class CitationResult(Contract):
    case_id: Identifier
    relevant_cited_source_ids: tuple[str, ...]
    unlabelled_cited_source_ids: tuple[str, ...]
    missing_relevant_source_ids: tuple[str, ...]


class RetrievalRecallResult(Contract):
    case_id: Identifier
    k: int = Field(gt=0)
    retrieved_source_ids_at_k: tuple[str, ...]
    found_relevant_source_ids: tuple[str, ...]
    missing_relevant_source_ids: tuple[str, ...]

    @property
    def recall_at_k(self) -> float:
        found = len(self.found_relevant_source_ids)
        return found / (found + len(self.missing_relevant_source_ids))


def _require_same_case(case: EvaluationCase, response: RecordedResponse) -> None:
    if case.case_id != response.case_id:
        raise ValueError(
            f"case ID mismatch: expected {case.case_id!r}, received {response.case_id!r}"
        )


def check_citation_ids(case: EvaluationCase, response: RecordedResponse) -> CitationResult:
    """Partition citations by relevance labels; unlabelled does not mean nonexistent."""
    _require_same_case(case, response)
    relevant = set(case.relevant_source_ids)
    cited = set(response.cited_source_ids)
    return CitationResult(
        case_id=case.case_id,
        relevant_cited_source_ids=tuple(s for s in response.cited_source_ids if s in relevant),
        unlabelled_cited_source_ids=tuple(s for s in response.cited_source_ids if s not in relevant),
        missing_relevant_source_ids=tuple(s for s in case.relevant_source_ids if s not in cited),
    )


def check_retrieval_recall(
    case: EvaluationCase, response: RecordedResponse, *, k: int
) -> RetrievalRecallResult:
    """Recall@K = labelled relevant IDs in the top K / all labelled relevant IDs.

    Dataset contracts require at least one relevant ID and unique retrieval IDs.
    Fewer than K results are allowed; the denominator is never the result count.
    """
    _require_same_case(case, response)
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer (not a boolean)")
    top_k = tuple(response.retrieved_source_ids[:k])
    retrieved = set(top_k)
    return RetrievalRecallResult(
        case_id=case.case_id,
        k=k,
        retrieved_source_ids_at_k=top_k,
        found_relevant_source_ids=tuple(s for s in case.relevant_source_ids if s in retrieved),
        missing_relevant_source_ids=tuple(s for s in case.relevant_source_ids if s not in retrieved),
    )
