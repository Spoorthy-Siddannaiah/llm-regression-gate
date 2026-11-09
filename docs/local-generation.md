# Local Ollama recording

For a single opt-in command that captures a target, records a separate candidate,
and compares it, see the [local candidate workflow](local-candidate-workflow.md).

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

## Current generation configuration

- Local endpoint: `http://127.0.0.1:11434`.
- Installed model: `llama3.2:latest`, 3.2B parameters, Q4_K_M.
- Required model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`.
- Prompt/schema: `grounded-json-v2-citation-enum`, configuration 1.1.0 (with a
  `-topK` suffix when K differs from 3). System text is unchanged; each request's
  JSON schema restricts citation items to the exact retrieved source IDs.
  With no retrieved passages, `maxItems: 0` permits only an empty citation list.
  Full system message and schema are preserved in evidence.
- Generation: temperature 0, seed 42, context 4096, maximum output 256 tokens.
- Retrieval: `bm25-v1`, k1 1.2, b 0.75, top 3.
- Timeout: 180 seconds per local HTTP request; no automatic retries.

These settings reduce sampling variability but do not guarantee identical results
across model/runtime/hardware versions. The digest is verified before and after
the run. A differently installed model requires an explicit configuration/code
change; an existing model tag is not automatically trusted.

The historical v1 recordings used an unconstrained string array under
`grounded-json-v1`, configuration 1.0.0. They remain unchanged and replayable.
The observed invalid citation contained one extra character compared with a
retrieved ID. The new enum is intended to prevent that decoding choice, rather
than rewriting the model's output afterward. The parser still preserves unknown
IDs if a provider returns them; the independent corpus-membership gate remains.
This constraint does not establish relevance or factual support and may affect
answer quality or latency. A subsequent
[actual 25-case candidate](../recordings/squad/llama3.2-bm25-citation-enum-v2/README.md)
produced zero unknown IDs, retained the aggregate metrics, and passed the unchanged
v2 policy. That verifies the observed run's result, not universal runtime compliance
or correctness on other inputs. The parser still preserves invalid IDs if returned.

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

An existing output directory is refused. `--top-k` defaults to 3 and can change
the passage budget for a candidate experiment. The recording configuration and
manifest include the selected K; this does not change evaluation Recall@K settings.
`--limit 1` makes a smoke subset, explicitly identified in its manifest. It cannot
substitute for a complete recording in a comparison against the full dataset.
A failed run leaves evidence but no completed manifest; inspect it and choose a
new directory rather than overwriting.

Each successful run stores:

- `recording.json`: existing typed recording contract for offline comparison.
- `evidence/*.request.json` and `*.response.json`: actual prompts, raw responses,
  and Ollama-reported timing/token counts. These are run evidence, not controlled
  performance benchmarks.
- `started.json`: original run marker; completion is determined by `manifest.json`.
- `code-provenance.json`: Git commit/dirty status at capture and source/config hashes.
- `manifest.json`: model/server metadata, input/artifact hashes, options, runtime
  information, and `completed_not_promoted` status. Local model filesystem paths
  and unnecessary tensor listings are omitted from portable model metadata.

## Code provenance for future recordings

Before contacting Ollama or creating the output directory, the recorder captures
the current Git HEAD and whether the working tree is dirty. Git commands are
read-only; no remote URL, credentials, status filenames, or diff content are saved.
If Git metadata cannot be read, its status is `unavailable` and commit/dirty fields
are null, never an invented revision or a false clean state.

The snapshot hashes the recorder script, the local workflow wrapper when present, every Python file under
`src/llm_reliability`, `pyproject.toml`, and `uv.lock`, using project-relative paths.
Hashing the whole package avoids overlooking imported helpers. The trade-off is
that even an unrelated package edit can stop a long generation run. Source paths
cannot escape the project through symlinks. No secrets/environment files are read.

The recorder checks that file hashes and the covered file set remain unchanged
after generation and before writing the completed recording/manifest. Drift leaves
raw evidence for inspection but no completed recording. `code-provenance.json`
is hashed in the manifest and its content is also stored under `code_provenance`.

Historical recordings are not backfilled. Replay validates this optional metadata
and its sidecar when present, but does not compare historical hashes with today's
checkout: a baseline must remain replayable after code changes. Dirty source
contents are not bundled, so a Git revision alone cannot reconstruct a dirty run.
This is a source-tree snapshot, not signed attestation of executed code or proof
that candidate outputs belong to the current PR. It does not guarantee deterministic
generation or install dependencies to match the saved lockfile automatically.

## Review before acceptance

Completing a run proves execution, not quality. Evaluate the recording and inspect
case evidence before using it as a reference. A self-comparison can measure absolute
quality floors, but its zero deltas do not prove improvement or regression safety.
Preserve failures rather than regenerating until the run passes or lowering
thresholds merely to obtain a green gate. The first-span answer check and source
labels retain the limitations documented in the SQuAD dataset README.

Implementation references: [Ollama chat API](https://docs.ollama.com/api/chat),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
