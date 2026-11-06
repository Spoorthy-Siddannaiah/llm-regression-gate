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
