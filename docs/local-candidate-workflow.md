# One opt-in local candidate workflow

`scripts/run_local_candidate.py` connects code-target capture, new local generation,
and strict comparison. Invoking it makes local Ollama calls; it is separate from
the offline comparison CLI and is **not enabled in GitHub Actions**.

## Run when local inference is intended

The pinned installed Llama 3.2 model and a running local Ollama server are required.
No model is downloaded, no server is started, and no hosted provider is selected
automatically. From the repository root:

```sh
uv run --python 3.12 scripts/run_local_candidate.py \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --policy configs/gate.citation-v2.json \
  --settings configs/evaluator.v1.json \
  --recording-id squad-local-candidate-new \
  --top-k 3 \
  --output-dir reports/local-candidate-new
```

Use a new output directory and recording ID. No particular model score or exit
0/1 is promised: output depends on the actual run and selected policy. The baseline
is an observed reference with known failures, not a release-approved pipeline.

`--policy` is required to make the quality criteria explicit. `--top-k` controls
generation's passage budget; `--settings` controls shared evaluation settings and
is optional. There is no partial-dataset `--limit` mode in this wrapper.

## Stages

1. Validate dataset/baseline compatibility, manifests, policy, settings, and arguments
   before generation. Refuse existing output and output nested inside the baseline run.
2. Capture an expected Git/source snapshot and input hashes, then create the new run.
   Available Git metadata is required for strict candidate freshness.
3. Invoke the existing recorder in a separate Python process, writing a fresh candidate.
   Only questions and retrieved passages enter its model prompt.
4. Reject covered code changes or changes to dataset, corpus, baseline recording/manifest,
   policy, or settings. Do not compare if generation fails.
5. Invoke the existing comparison CLI with required manifests and the captured expected
   candidate code target. Baseline code is not required to match the new target.
6. Recheck code/input stability, report identities, and outcome; require both reports.
   Save completion metadata with report hashes. Never promote or replace the baseline.

The conservative code snapshot includes the wrapper, recorder, package Python
files, and dependency configuration. Git status can become dirty when artifacts
are written; covered hashes and revision matching retain the freshness contract.

## Output layout

```text
new-run/
├── expected-code.json
├── started.json          # input hashes; run remains incomplete without completion marker
├── candidate/
│   ├── recording.json
│   ├── manifest.json
│   ├── code-provenance.json
│   └── evidence/         # exact requests/responses
├── reports/
│   ├── report.json
│   └── report.md
└── completed.json        # outcome, exit code, report hashes; baseline_promoted=false
```

| Exit | Meaning | Completion marker |
| --- | --- | --- |
| 0 | Generation and strict comparison completed; gate passed | `gate_passed` |
| 1 | Generation and strict comparison completed; gate failed | `gate_failed` |
| 2 | Invalid input, generation/freshness failure, drift, timeout, or report error | Absent or incomplete |

A quality failure is a completed evaluation, not a generation error. Partial evidence
is retained on errors; even reports may exist before a later stability check fails.
Use the process outcome and completion marker together, and retry in a new directory.
An I/O error can leave a partial marker or report; file presence alone is not proof
of completion. Require valid completion metadata and matching report hashes.
Generation has a one-hour subprocess timeout and comparison a two-minute timeout;
the recorder retains its 180-second per-request timeout. Timeouts do not promote output.

## What was verified

Tests exercise the actual recorder and actual comparison CLI with mocked Ollama
responses on the real dataset. They cover pass/fail, provenance freshness, baseline
preservation, preflight rejection, generation errors/timeouts, code/input drift,
comparison errors, and missing reports. Mocked outputs are test-only, not new model
benchmark results. This implementation task made no real Ollama calls and did not
regenerate or modify the historical recordings.

This is an explicitly invoked **local** workflow. It is not PR-triggered generation,
signed execution attestation, a production release approval process, or deployment.
Offline replay remains available without Ollama. Optional report diagnostics can
be added in a later offline replay using the saved candidate; they are not wrapper
options in this bounded implementation.
