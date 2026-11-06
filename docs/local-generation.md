# Local Ollama recording

This path makes actual local model calls only when explicitly invoked. CI and the
comparison CLI still consume recordings without a running Ollama server. There is
no automatic model download, fallback provider, or baseline replacement.

## Pipeline and data boundary

```text
SQuAD question -> BM25 top 3 corpus passages -> Ollama -> typed response -> recording
                                                     -> raw request/response evidence
```

Only the question and retrieved source IDs/text enter the model prompt. Dataset
fact assertions, associated-source labels, and reference answers do not. Responses
request short answers with citations via a JSON schema. Unknown or empty citations
are preserved; no labels are used to repair them. Malformed or truncated responses
stop the run instead of silently skipping a case or manufacturing an answer.

## Fixed v1 configuration

- Local endpoint: `http://127.0.0.1:11434`.
- Installed model: `llama3.2:latest`, 3.2B parameters, Q4_K_M.
- Required model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`.
- Prompt: `grounded-json-v1`; full system message and schema are preserved in evidence.
- Generation: temperature 0, seed 42, context 4096, maximum output 256 tokens.
- Retrieval: `bm25-v1`, k1 1.2, b 0.75, top 3.
- Timeout: 180 seconds per local HTTP request; no automatic retries.

These settings reduce sampling variability but do not guarantee identical results
across model/runtime/hardware versions. The digest is verified before and after
the run. A differently installed model requires an explicit configuration/code
change; an existing model tag is not automatically trusted.

## Run

Start the already installed Ollama service separately if needed (`ollama serve`).
Then, from the repository root:

```sh
uv run --python 3.12 scripts/record_ollama.py \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json \
  --recording-id squad-llama3.2-bm25-new-run \
  --output-dir recordings/squad/new-run
```

An existing output directory is refused. `--limit 1` makes a smoke subset; its
manifest identifies that scope and it cannot substitute for a complete recording
in a comparison against the full dataset. A failed run leaves evidence but no
completed manifest; inspect it and choose a new directory rather than overwriting.

Each successful run stores:

- `recording.json`: existing typed recording contract for offline comparison.
- `evidence/*.request.json` and `*.response.json`: actual prompts, raw responses,
  and Ollama-reported timing/token counts. These are run evidence, not controlled
  performance benchmarks.
- `started.json`: original run marker; completion is determined by `manifest.json`.
- `manifest.json`: model/server metadata, input/artifact hashes, options, runtime
  information, and `completed_not_promoted` status. Local model filesystem paths
  and unnecessary tensor listings are omitted from portable model metadata.

## Review before acceptance

Completing a run proves execution, not quality. Evaluate the recording and inspect
case evidence before using it as a reference. A self-comparison can measure absolute
quality floors, but its zero deltas do not prove improvement or regression safety.
Preserve failures rather than regenerating until the run passes or lowering
thresholds merely to obtain a green gate. The first-span answer check and source
labels retain the limitations documented in the SQuAD dataset README.

Implementation references: [Ollama chat API](https://docs.ollama.com/api/chat),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
