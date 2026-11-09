# Actual constrained-citation candidate

Recorded locally on 2026-11-09 using the installed pinned Llama 3.2 model, BM25
top 3, and the unchanged 25-case SQuAD slice. These are real model responses,
not handwritten fixtures or copied reference answers. The baseline remains
`../llama3.2-bm25-v1/recording.json` and is not replaced.

## Controlled change and result

The request JSON schema now enumerates the retrieved source IDs as valid citation
choices (`grounded-json-v2-citation-enum`, configuration 1.1.0). System text, user
messages, model digest, generation options, and retrieval are unchanged. Tests
compare all 25 saved requests and verify the enum is their only request difference.

| Check | Fixed baseline | Candidate |
| --- | ---: | ---: |
| Required-phrase coverage | .84 | .84 |
| Citation-label coverage | .80 | .80 |
| Retrieval Recall@3 | .84 | .84 |
| Unknown citation occurrences | 1 | 0 |

The unchanged `gate.citation-v2.json` policy passes: exit 0. Only case
`squad-56e17644e3433e1400422f40` differs in recorded observations; its answer is
unchanged and the previously corrupted citation now matches a retrieved ID.
All 54 baseline files matched their pre-run hashes. Nothing was silently repaired.

## Evidence and replay

`evidence/` contains the exact request/response pairs. `manifest.json` hashes the
recording, code snapshot, and evidence. `expected-code.json` is the wrapper's
independently captured pre-generation target. Target revision:
`bb71ce1f947cff3fef80874dae1ade680afd6249`.
The snapshot and recorder agree on revision and source hashes. This is historical
target validation, not a claim that the recording came from a later PR checkout.

The wrapper completed locally with `gate_passed`, exit 0, and
`baseline_promoted=false`. Wrapper completion metadata and generated reports remain
in the ignored local run directory `runs/squad-citation-enum-20261109-v1/`.
The portable recording and raw evidence here are retained for replay without Ollama.

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-citation-enum-v2/recording.json \
  --expected-candidate-code recordings/squad/llama3.2-bm25-citation-enum-v2/expected-code.json \
  --policy configs/gate.citation-v2.json \
  --settings configs/evaluator.v1.json \
  --output-dir reports/citation-enum-replay-new
```

Choose a new output directory. Expected: schema-3 reports, no failures, exit 0.
Passing this limited policy does not establish semantic correctness or production
release approval. A valid source ID may still be irrelevant or fail to support
an answer. Results are from one local run, not a statistical evaluation.

Source passages and questions derive from SQuAD; its attribution and CC BY-SA 4.0
notice are in [the dataset README](../../../datasets/squad/v1/README.md).
