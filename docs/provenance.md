# Recording provenance checks

Real replay now checks file integrity before scoring. This catches stale recordings
even when someone leaves the dataset's version label unchanged. It makes no model
calls and does not modify the dataset, recording, manifest, or baseline.

## When validation applies

`load_comparison` still uses `ComparisonInput` for dataset identity/version and
exact case coverage. After that, it requires manifests for both recordings if:

- `require_manifests=True` / CLI `--require-manifests` is set;
- an explicit `sources_path` / CLI `--sources` is supplied;
- either recording directory contains `manifest.json`; or
- either model version contains `@sha256:` (our actual local recordings).

The final condition prevents deleting both sidecars from silently downgrading the
real examples to fixture-only validation. Synthetic recordings without manifests
or model digests keep their existing loading behaviour. CI explicitly requires
manifests for the real SQuAD replays.

Manifests live beside each recording. If sources are not explicitly supplied,
validation uses `sources.json` beside the dataset. Explicit paths are preferable
for nonstandard layouts. This schema currently supports the local Ollama v1
recorder; it is not a universal manifest standard for other providers.

## What is checked

- Supported manifest version, completed status, full-dataset scope, recording ID,
  and response count.
- Model name/digest, prompt version, and retrieval version/top K against recording
  configuration. Intentional differences between baseline and candidate remain
  allowed; each must match its own manifest.
- SHA-256 of the exact supplied dataset and corpus bytes against both manifests.
- Hash entries for the recording, start marker, and every numbered request/response
  evidence pair. Every listed artifact must exist and match its hash.
- Artifact paths must stay inside the recording directory, including after symlink
  resolution. Absolute paths, parent traversal, and backslashes are rejected.

The typed manifest reader ignores additional metadata fields while validating all
fields it consumes. Existing complete manifests remain unchanged. Reformatting an
input JSON file changes its byte hash and therefore invalidates the old recording.

New recordings may include typed `code_provenance` metadata. If present, the
manifest must hash `code-provenance.json`, and that sidecar must exactly match the
metadata. A sidecar without its manifest metadata is rejected rather than silently
treated as a legacy recording. Existing manifests without either remain valid.
The reader checks metadata consistency, not current-checkout source files, so old
baselines remain replayable. See [capture semantics and limits](local-generation.md#code-provenance-for-future-recordings).
For an explicit target, `--expected-candidate-code` adds commit/source-hash equality
for the candidate only; see [freshness semantics](candidate-freshness.md).

## CLI example

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.relative-only.v1.json \
  --settings configs/evaluator.v1.json \
  --output-dir reports/squad-verified-new-run
```

Valid provenance permits scoring, so this known regressed candidate still exits 1
and writes reports. Stale or incompatible provenance exits 2, with the role,
manifest/file path, and field/hash detail, before scoring or report writing. This
distinguishes unreliable evaluation inputs from observed poor application quality.

## Limits

Hashes detect file drift relative to the manifest; they are not signatures. They
cannot prove authenticity if someone rewrites both artifacts and hashes, or prove
that recorded output came from the current pull request's code. Review and future
fresh-candidate generation remain necessary. The checks do not establish semantic
correctness or release acceptance. Default reports retain schema 1; optional
alternative-answer reports use schema 2. Neither embeds a separate provenance-validation receipt.
