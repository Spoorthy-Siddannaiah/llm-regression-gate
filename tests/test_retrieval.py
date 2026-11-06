from math import log1p
from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_reliability.loading import InputLoadError, load_corpus, load_dataset
from llm_reliability.retrieval import BM25Retriever, RetrievalSettings, SourceCorpus


def test_score_matches_hand_calculated_bm25():
    retriever = BM25Retriever(SourceCorpus({"a": "cat cat dog", "b": "dog"}))
    hit, = retriever.retrieve("cat", top_k=2)
    expected = log1p(1.5 / 1.5) * 2 * 2.2 / (2 + 1.2 * (0.25 + 0.75 * 3 / 2))
    assert hit.source_id == "a"
    assert hit.score == pytest.approx(expected)


def test_ranking_ties_and_corpus_order_are_deterministic():
    sources = {"b": "cat dog", "a": "cat dog", "c": "unrelated"}
    first = BM25Retriever(SourceCorpus(sources)).retrieve("CAT!!! cat", top_k=5)
    second = BM25Retriever(SourceCorpus(dict(reversed(list(sources.items()))))).retrieve("cat", top_k=5)
    assert first == second
    assert [hit.source_id for hit in first] == ["a", "b"]


@pytest.mark.parametrize("question", ["", "\n \t", "?!", "absentword"])
def test_no_matching_tokens_returns_no_hits(question):
    assert BM25Retriever(SourceCorpus({"a": "cat"})).retrieve(question) == ()


def test_input_is_snapshotted_and_source_text_preserved():
    corpus = SourceCorpus({"a": "Cat, DOG!"})
    retriever = BM25Retriever(corpus)
    corpus.root["a"] = "later modification"
    hit, = retriever.retrieve("cat")
    assert hit.text == "Cat, DOG!"


@pytest.mark.parametrize("top_k", [0, -1, True, 1.2, "3"])
def test_invalid_top_k_rejected(top_k):
    with pytest.raises(ValueError, match="positive integer"):
        BM25Retriever(SourceCorpus({"a": "cat"})).retrieve("cat", top_k=top_k)


@pytest.mark.parametrize("corpus", [{}, {"": "text"}, {" a": "text"}, {"a": "?!"}, {"a": 12}])
def test_malformed_corpus_rejected(corpus):
    with pytest.raises(ValidationError):
        SourceCorpus(corpus)


@pytest.mark.parametrize("settings", [{"k1": 0.0}, {"k1": float("inf")}, {"b": -0.1}, {"b": 1.1}, {"b": True}])
def test_invalid_settings_rejected(settings):
    with pytest.raises(ValidationError):
        RetrievalSettings(**settings)


def test_bad_corpus_file_identifies_path(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text('{"a": ""}')
    with pytest.raises(InputLoadError) as caught:
        load_corpus(path)
    assert str(path) in str(caught.value)
    assert "source 'a'" in str(caught.value)


def test_real_squad_retrieval_uses_questions_and_corpus_only():
    directory = Path(__file__).resolve().parents[1] / "datasets/squad/v1"
    corpus = load_corpus(directory / "sources.json")
    dataset = load_dataset(directory / "dataset.json")
    retriever = BM25Retriever(corpus)
    # Labels are used only to assess results after retrieval, never passed to it.
    question = dataset.cases[0].question
    hits = retriever.retrieve(question, top_k=3)
    assert hits == retriever.retrieve(question, top_k=3)
    assert 0 < len(hits) <= 3
    assert len({hit.source_id for hit in hits}) == len(hits)
    assert all(hit.text == corpus.root[hit.source_id] for hit in hits)
    assert dataset.cases[0].relevant_source_ids[0] in {hit.source_id for hit in hits}
