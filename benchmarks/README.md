# Reproducible retrieval measurements

`squad-bm25-v1.json` contains measured rankings and scores for all 25 questions
against the 50-passage real SQuAD slice. It was generated locally on Python 3.12.13,
not copied from a leaderboard. Input hashes and retriever settings are preserved.

| Metric | Value | Associated paragraph found |
| --- | ---: | ---: |
| Recall@1 | 0.68 | 17 / 25 |
| Recall@3 | 0.84 | 21 / 25 |
| Recall@5 | 0.88 | 22 / 25 |

Each case has one associated-source label, so mean recall equals the fraction of
questions whose labelled source appears in the top K. Other retrieved passages
may also be relevant. This is a small, deliberately selected integration slice,
not an official full-corpus SQuAD retrieval benchmark or a generalization claim.
No answer generation, model baseline, latency benchmark, or cost experiment is
included. These scores were observed, not tuned to meet a release threshold.

Reproduce from the repository root, using a new output filename:

```sh
uv run --python 3.12 scripts/evaluate_retrieval.py \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json \
  --output reports/retrieval-run-001.json
```

The script reuses the existing Recall@K check after retrieval. It reads labels only
to assess the returned rankings; the retriever sees only questions and source text.
Empty answer fields used internally to adapt the metric interface are not model
outputs and are not saved as a `Recording`.

The code uses BM25 with k1=1.2, b=0.75 and positive log IDF. Its IDF and parameter
meanings follow [Lucene's BM25 documentation](https://lucene.apache.org/core/9_12_1/core/org/apache/lucene/search/similarities/BM25Similarity.html).
The Python scorer uses exact token lengths, term-frequency saturation with the
`k1+1` factor, and a simple tokenizer; scores are not claimed identical to Lucene.
Tokenization case-folds Unicode word tokens, retains stopwords and numbers, and
does not stem. Repeated query terms count once. Zero-score passages are omitted;
ties break by source ID. Floating-point scores can vary slightly across platforms;
tests compare rankings and recall rather than exact score bytes.

## Real RAG candidate comparison

[`squad-top1-experiment-v1.json`](squad-top1-experiment-v1.json) preserves the actual
gate result and unchanged-baseline hashes for a separate local generation run.
Only the intended passage budget changes: three -> one. Model digest, corpus,
questions, generation/prompt settings, server, and BM25 configuration match.

| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Required-phrase coverage | 0.84 | 0.68 | -0.16 |
| Citation-label coverage | 0.80 | 0.68 | -0.12 |
| Retrieval Recall@3 | 0.84 | 0.68 | -0.16 |

The zero-drop, zero-floor relative policy fails on all three drops. This avoids
confusing genuine relative changes with the baseline's existing absolute-floor
failures. Both sides are evaluated with the same K=3; the candidate returns only
one source. This measures coverage lost to the smaller budget, not degraded BM25
ranking. Single-run answer differences are not a statistical causal estimate.
No latency or cost improvement was measured or claimed. Raw timing/token fields
are preserved in each run's evidence for inspection only.

See [candidate recording and replay command](../recordings/squad/llama3.2-bm25-top1-v1/README.md).

## Alternative-answer diagnostic

[`squad-alternatives-v1.json`](squad-alternatives-v1.json) measures a separate OR
check over deduplicated human answer annotations. Coverage stays 0.84/0.68 for
baseline/candidate; no score improvement is claimed. Source spans and case coverage
are validated, and input hashes/per-case evidence are preserved. Existing v1 gates
and recordings are unchanged. See [semantics and reproduction](../docs/answer-alternatives.md).
