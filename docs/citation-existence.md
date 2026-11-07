# Citation existence: corpus membership only

The new `citation-existence-v1` diagnostic looks up each cited ID in the full
supplied corpus, independently of relevance labels and retrieval results.

For a corpus containing IDs `doc-1` and `doc-2`:

| Cited ID | Result | Meaning |
| --- | --- | --- |
| doc-1 | Existing | The ID is in this corpus snapshot |
| doc-2, when only doc-1 is labelled relevant | Existing | Unlabelled does not mean nonexistent |
| doc-99 | Unknown | The ID is absent from this corpus snapshot |
| No citations | N/A | No citation-existence evidence; reported separately |

This is a deterministic, case-sensitive lookup using the validated recorded IDs.
It does not use fuzzy matching, an LLM judge, or relevance labels to classify
existence. The check preserves existing and unknown IDs in their original order.
An existing source may not have been retrieved, may be irrelevant, and may fail
to support the answer. Unknown IDs may be invented, mistyped, stale, or valid in
some other corpus; their cause is not established by this check.

## Run and inspect

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.relative-only.v1.json \
  --settings configs/evaluator.v1.json \
  --citation-existence \
  --output-dir reports/citation-existence-new
```

`--citation-existence` adds `diagnostics.citation_existence` to schema-2 JSON and
a labelled Markdown section. It can be combined with `--answer-alternatives`.
Without either flag, default schema-1 output remains unchanged. Without an explicit
`--sources`, the corpus defaults to `sources.json` beside the dataset.

The output includes corpus SHA-256, source count, recording IDs, per-case existing
and unknown IDs, aggregate citation counts, and cases without citations.
`all_cited_ids_exist` is null/N/A when no citations exist, rather than vacuously true.
Counts represent citation occurrences across requests, not unique IDs over the run.

Real recording provenance binds this supplied corpus to the generation run. Plain
synthetic fixtures lack that historical guarantee. A missing/invalid requested
corpus is an input error (exit 2); no diagnostic is silently dropped.
No model calls are made. The diagnostic does not change the gate or exit 0/1 decision.
An independently selected [v2 policy](citation-gate-v2.md) can enforce this same
membership evidence; the report-only flag itself still does not change enforcement.

## Measured real recording results

| Recording | Existing citation occurrences | Unknown occurrences | Cases without citations |
| --- | ---: | ---: | ---: |
| Baseline | 34 | 1 | 3 |
| Top-one candidate | 20 | 0 | 5 |

The baseline's unknown ID occurs in `squad-56e17644e3433e1400422f40`. It is preserved
in the original recording. Measurement:
[`benchmarks/squad-citation-existence-v1.json`](../benchmarks/squad-citation-existence-v1.json).
The candidate has no unknown cited IDs but still fails the existing gate because
answer-phrase and source-coverage metrics regressed. No-citation cases do not count
as evidence of good citations. None of these results establish semantic support.
