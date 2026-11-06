"""Small in-memory BM25 retriever: questions and corpus only, never answer labels."""

from collections import Counter
from math import fsum, log1p
import re
from typing import Literal, Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from llm_reliability.models import Contract, Identifier


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


class SourceCorpus(RootModel[dict[str, str]]):
    model_config = ConfigDict(strict=True)

    @model_validator(mode="after")
    def valid_sources(self) -> Self:
        if not self.root:
            raise ValueError("source corpus must not be empty")
        for source_id, text in self.root.items():
            if not source_id or source_id != source_id.strip():
                raise ValueError(f"source ID must be nonblank with no surrounding whitespace: {source_id!r}")
            if not _tokens(text):
                raise ValueError(f"source {source_id!r} has no searchable tokens")
        return self


class RetrievalSettings(Contract):
    model_config = ConfigDict(frozen=True)
    retriever_version: Literal["bm25-v1"] = "bm25-v1"
    tokenizer_version: Literal["unicode-word-casefold-v1"] = "unicode-word-casefold-v1"
    k1: float = Field(default=1.2, gt=0, allow_inf_nan=False)
    b: float = Field(default=0.75, ge=0, le=1, allow_inf_nan=False)


class RetrievalHit(Contract):
    source_id: Identifier
    text: str
    score: float = Field(gt=0, allow_inf_nan=False)


class BM25Retriever:
    """Score every paragraph, return positive-score hits with stable ID tie breaks.

    IDF = log(1 + (N - df + 0.5)/(df + 0.5)). Query terms contribute once.
    tf_weight = tf*(k1+1)/(tf + k1*(1-b+b*length/average_length)).
    This uses exact token lengths; it is not Lucene's compressed-norm implementation.
    """

    def __init__(self, corpus: SourceCorpus, *, settings: RetrievalSettings | None = None):
        self._settings = settings if settings is not None else RetrievalSettings()
        # Snapshot caller-owned input; retrieval does not modify corpus text.
        self._documents = tuple(sorted(corpus.root.items()))
        self._frequencies = tuple(Counter(_tokens(text)) for _, text in self._documents)
        self._lengths = tuple(sum(counts.values()) for counts in self._frequencies)
        self._average_length = sum(self._lengths) / len(self._documents)
        self._document_frequency: Counter[str] = Counter()
        for counts in self._frequencies:
            self._document_frequency.update(counts.keys())

    @property
    def settings(self) -> RetrievalSettings:
        return self._settings

    def retrieve(self, question: str, *, top_k: int = 3) -> tuple[RetrievalHit, ...]:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k must be a positive integer (not a boolean)")
        terms = sorted(set(_tokens(question)))
        if not terms:
            return ()
        k1, b = self.settings.k1, self.settings.b
        size = len(self._documents)
        hits = []
        for (source_id, text), counts, length in zip(
            self._documents, self._frequencies, self._lengths, strict=True
        ):
            normalization = k1 * (1 - b + b * length / self._average_length)
            score = fsum(
                log1p((size - self._document_frequency[term] + 0.5)
                      / (self._document_frequency[term] + 0.5))
                * counts[term] * (k1 + 1) / (counts[term] + normalization)
                for term in terms if term in counts
            )
            if score > 0:
                hits.append(RetrievalHit(source_id=source_id, text=text, score=score))
        return tuple(sorted(hits, key=lambda hit: (-hit.score, hit.source_id))[:top_k])
