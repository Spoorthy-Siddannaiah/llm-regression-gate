# Opt-in candidate code freshness

`--expected-candidate-code expected.json` requires the candidate's saved code
provenance to match an explicitly supplied target. It applies only to the candidate;
the fixed baseline may have older code metadata or no code snapshot at all.
Ordinary manifest/data/evidence integrity checks still apply to both recordings.

## Exact contract

- Both candidate and target must have available Git revisions.
- Git commits must match exactly, even if a different commit changes only documentation.
- The complete covered source-file set and every SHA-256 must match.
- Dirty flags are informational. Writing artifacts or changing unrelated files can
  change dirty state without changing the covered code; hashes still have to match.

An absent snapshot, unavailable Git revision, changed hash/file set, or wrong commit
is an **input error: exit 2 before scoring or report writing**. Passing freshness
only permits evaluation: the quality gate can still fail with exit 1.

## Intended workflow for a new recording

Capture the target from the intended checkout before generation, preferably after
committing the intended code. Use a new output filename:

```sh
uv run --python 3.12 scripts/capture_code_provenance.py \
  --output reports/expected-candidate-code-new.json
```

The script captures only local metadata/hashes and refuses to overwrite a file.
`--project-root` can explicitly select the target checkout. It does not contact
Ollama or create a model recording. It fails rather than inventing a Git revision.

After separately generating a **new** candidate with `scripts/record_ollama.py`,
use the existing comparison command with this additional option:

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/new-candidate/recording.json \
  --expected-candidate-code reports/expected-candidate-code-new.json \
  --policy configs/gate.relative-only.v1.json \
  --output-dir reports/fresh-candidate-new
```

`new-candidate` is a placeholder for a future generated run, not a bundled artifact.
Both existing real recordings predate code-snapshot capture. They still replay
normally, but cannot satisfy this optional freshness requirement. They are not
backfilled or regenerated to make it pass.

The baseline intentionally remains exempt from target-code equality: comparison
against an older implementation is precisely the purpose of a baseline. Default
replay and report schemas/bytes remain unchanged. With the flag, CLI success output
confirms freshness validation; the reports do not yet include a separate receipt.

## Limits

The caller must capture the target from the intended code revision. Supplying the
candidate's own old snapshot as its target does not establish freshness to a new PR.
This is metadata consistency against an explicit target, not signed execution
attestation or automatic current-checkout detection. Matching metadata cannot prove
authenticity if artifacts and their hashes are rewritten together. This feature
does not run changed PR prompts or generate new responses; generation remains opt-in.
