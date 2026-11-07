# Alternative-answer diagnostic

The new `alternative-phrases-v1` check is separate from the existing
`deterministic-v1` scorer and gate. Existing datasets, recordings, manifests,
thresholds, and historical reports remain unchanged.

## OR versus AND

`required_facts=["30 days", "proof of purchase"]` still requires **both** phrases.
An `AnswerAlternatives` expectation instead accepts **any one** listed variant:

```python
from llm_reliability.answer_alternatives import AnswerAlternatives, check_answer_alternatives

expectation = AnswerAlternatives(
    case_id="example", alternatives=["Norseman", "Viking"]
)
# check_answer_alternatives(expectation, response) accepts either phrase.
```

That example illustrates an explicitly authored expectation; it does not modify
SQuAD's annotations. The SQuAD diagnostic uses only whole reference-answer strings
actually present in `references.json`. Repeated human annotations are deduplicated
after case/whitespace normalization. No phrase is split into new aliases, and no
aliases are inferred from model answers. Authored duplicate/blank variants and
mismatched case IDs are explicit validation errors.

Matching is case-insensitive literal phrase presence with whitespace normalization,
word boundaries, and significant punctuation. It does not understand negation,
contradictions, units, or unannotated paraphrases. Finding one variant is not proof
that the full answer is correct. This is not official SQuAD exact-match/F1 scoring.

## Reproduce the real-data diagnostic

```sh
uv run --python 3.12 scripts/evaluate_answer_alternatives.py \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json \
  --references datasets/squad/v1/references.json \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --output reports/answer-alternatives-new.json
```

The script validates existing recording provenance, exact reference-case coverage,
associated-source labels, and annotated answer offsets against the source text.
It then saves input hashes and per-case results. Use a new output filename; existing
files are refused. A completed diagnostic exits 0 regardless of match rate; input
or output errors exit 2. It does not make release decisions or model calls.

Observed on the real 25-question recordings:

| Recording | Original required-phrase case coverage | Any annotated alternative |
| --- | ---: | ---: |
| Baseline | 0.84 | 0.84 |
| Top-one candidate | 0.68 | 0.68 |

Evidence: [`benchmarks/squad-alternatives-v1.json`](../benchmarks/squad-alternatives-v1.json).
The result did not improve. In particular, “9 miles” is supported by the passage
but absent from the stored reference alternatives, so it still does not match.
Any new accepted alias needs explicit annotation review and versioning rather than
silently changing labels to fit generated responses.

## Optional evidence in comparison reports

The main comparison CLI can compute this same diagnostic and attach it to both
reports in one invocation:

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.relative-only.v1.json \
  --settings configs/evaluator.v1.json \
  --answer-alternatives datasets/squad/v1/references.json \
  --output-dir reports/squad-alternatives-new
```

Without the flag, schema-1 JSON/Markdown output is unchanged. With the flag, reports
use schema 2 and add `diagnostics.answer_alternatives` to JSON plus a clearly labelled
Markdown section containing aggregate coverage, allowed/matched/unmatched phrases,
and diagnostic input hashes. The original gate result, thresholds, metrics, and
failures stay identical. For the regressed candidate above, both modes exit 1.
An unchanged-baseline comparison still exits 0 under the relative-only policy,
even when some diagnostic checks fail. Bad requested references instead exit 2
before report writing; they are not silently omitted.

Both the standalone script and CLI use shared typed diagnostic code. Programmatic
rendering accepts `answer_alternatives=diagnostic` built by `build_diagnostic` in
`llm_reliability.alternative_diagnostics`. Use the same input files as the gate
evaluation; renderers reject mismatched recording IDs, case ordering/counts, or v1
case outcomes. Computed result models are output objects, not a persistence input API.
This feature is report-only: no alternative metric is used to approve a release.
