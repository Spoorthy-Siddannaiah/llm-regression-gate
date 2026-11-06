# Observed local RAG baseline v1

These are actual local Ollama outputs from all 25 real SQuAD questions, not
synthetic fixtures or copied reference answers. They form a fixed **observational
reference**, not a release-approved quality baseline. No automatic promotion occurred.

Configuration: Llama 3.2 3.2B Q4_K_M, Ollama 0.33.3, BM25 top 3, temperature 0,
seed 42, context 4096, output cap 256. The complete model digest, input hashes,
settings, timestamps, and raw request/response evidence are in `manifest.json`.
It intentionally omits the local filesystem path from model metadata. Request and
response content has not been repaired or edited. Input/output token counts and
timings in raw responses are single-run evidence, not controlled benchmarks.

## Measured review

| Check | Result |
| --- | ---: |
| Required first-answer phrase present | 21/25 (84%) |
| Associated source cited | 20/25 (80%) |
| Associated source retrieved at K=3 | 21/25 (84%) |
| Empty answers | 1 |
| Cited IDs absent from the corpus | 1 |

The existing citation metric measures associated-source coverage, not precision
or semantic support. An unlabelled citation is not necessarily nonexistent; the
absent ID count above was separately checked against the actual corpus.

Self-comparing this recording with illustrative 90% absolute floors fails all
three metric floors. Deltas are zero by construction; this is an absolute-quality
diagnostic, not a claim that a candidate regressed. These floors are **not calibrated
production acceptance requirements**. Do not lower them merely to green this run.

Reproduce the offline review with a new output directory:

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-v1/recording.json \
  --policy configs/gate.squad-review.v1.json \
  --settings configs/evaluator.v1.json \
  --output-dir reports/squad-review-new-run
```

Expected exit: 1, with reports. This command makes no model calls.

## Case review and limits

- `squad-57337ddc4776f41900660bbb`: model answers “9 miles”; the context explicitly
  pairs that distance with “15 kilometres”. The literal first-span checker flags
  this supported alternative expression. Keep it visible as a metric limitation.
- `squad-56dde0379a695914005b9636`: model explains Norman as people from Normandy,
  missing the original “Norseman, Viking” meaning. The associated paragraph was
  absent from the top three results.
- `squad-56dfa0d84a1a83140091ebb7`: empty answer for Tesla's death year; the associated
  source containing 1943 was absent from the top three results.
- `squad-56e16839cd28a01900c67887`: answers “Computational complexity” rather than the
  significant-resources criterion, despite retrieving the associated paragraph.
- `squad-56e17644e3433e1400422f40`: includes one citation ID not found in the corpus.
  It remains unchanged in the recording and raw evidence.

These observations are not a semantic accuracy score. The small selected corpus,
nonexhaustive labels, and first-span phrase checks retain their documented limits.
The model may have encountered SQuAD during pretraining; no unseen-data claim is made.

Inputs and contexts derive from [the licensed SQuAD slice](../../../datasets/squad/v1/README.md).
Requests reproduce adapted SQuAD text under CC BY-SA 4.0 with attribution in that
README. Ollama's model license is retained in the manifest; no model weights are
redistributed. See [local generation instructions](../../../docs/local-generation.md).
