# Progress

## Completed: scaffolding and typed evaluation contracts

- Confirmed the workspace was empty and independent from the Databricks Copilot.
- Added Python packaging, locked dependencies, Git exclusions, and working instructions.
- Added dataset, configuration, recording, and comparison models with strict validation.
- Added two fictional support-policy cases and their source documents.
- Verified with Python 3.12.13: `uv run --python 3.12 pytest` — 19 passed.
- Fixed package discovery after the initial editable build exposed a package-name mismatch.

## Completed: synthetic recordings and validated loading

- Added explicitly synthetic baseline/candidate recordings, separate from the dataset.
- Candidate intentionally changes the critical refund answer to 60 days and omits
  proof of purchase; no actual model or prompt experiment was performed.
- Added read-only UTF-8 JSON loaders using existing Pydantic models and ComparisonInput.
- Errors identify files, nested invalid fields, duplicate values, and case coverage.
- Empty answers, unknown citations, and retrieval order survive loading unchanged.
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 42 passed.
- Saved technical practice questions in `docs/interview-questions.md` for review.

## Completed: deterministic required-fact checks

- Added `check_required_facts(case, response)` returning matched and missing phrases.
- Matching ignores case/repeated whitespace, preserves punctuation, and avoids
  partial word/number matches. It rejects mismatched case IDs and does not mutate inputs.
- Verified the synthetic candidate refund answer misses both required phrases,
  while baseline answers and the unchanged support-hours answer pass.
- Tests explicitly demonstrate limitations for negation and paraphrases.
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 56 passed.

## Completed: citation IDs and retrieval Recall@K

- Citation checks partition cited IDs into labelled relevant and unlabelled IDs,
  and list relevant IDs not cited. They do not establish source existence or support.
- Recall@K uses relevant IDs found in the first K results divided by all labelled
  relevant IDs. K must be a positive integer; empty/short result lists are allowed.
- Both synthetic recordings have Recall@1 of 1.0 and cite their labelled sources;
  the candidate still fails required-phrase checks. Fixtures were not changed.
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 72 passed.

## Completed: recording evaluation runner

- Added `evaluate_comparison` to apply all three checks to validated recordings.
- Results retain dataset/schema versions, recording IDs, configuration snapshots,
  criticality, evaluator version, and retrieval K. Cases follow dataset order.
- Both sides use identical settings; matching uses IDs rather than list positions.
- No baseline writes, aggregate gate decisions, reports, or CLI were added.
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 83 passed.
- Selected Haystack's official PubMedQA RAG evaluation example for later adaptation;
  see `docs/real-rag-example.md`. No integration, downloads, or live calls yet.

## Completed: comparison and regression gate

- Added `compare_and_gate` with a versioned, snapshotted policy and typed failures.
- Compares case-weighted mean phrase coverage, citation-label coverage, and Recall@K.
- Defaults allow no metric drops and reject missing phrases in critical candidate
  cases, including failures already present in the baseline. Metric floors default
  to zero and can be configured independently from permitted drops.
- Synthetic fixture fails: phrase coverage 1.0 -> 0.5 plus a critical refund failure.
- Tested passing/improved candidates, inclusive boundaries, invalid thresholds,
  source metric drops, absolute floors, and unchanged input models.
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 110 passed.

## Completed: JSON and Markdown reports

- Added deterministic JSON output with report schema version 1 and the full gate result.
- Markdown includes decision, versions, policy, metric deltas, failures, and case evidence.
- Added explicit UTF-8 writing into new directories only; existing output is preserved.
  Disk failures identify the destination and warn about possible partial output.
- Generated and inspected local synthetic reports under `reports/` (ignored by Git).
- Verified with Python 3.12.13: `.venv/bin/python -m pytest` — 119 passed.

## Completed: offline CLI and distinct exit codes

- Added `llm-reliability` and `python -m llm_reliability` entry points connecting
  existing loading, evaluation, gates, and reports. No live calls are performed.
- Exit 0 means pass, 1 means gate failure, 2 means invalid arguments/inputs or an
  execution error. Reporting errors take precedence over quality failures.
- Added optional typed JSON policy/settings loading and explicit example configs.
- Both pass/fail write reports; existing output is refused. Baseline remains fixed.
- Verified 133 tests on Python 3.12.13 and installed console command exits 0/1/2.

## Completed: GitHub Actions replay checks

- Added `.github/workflows/regression.yml` for pull requests, pushes, and manual runs.
- Installs Python 3.12.13 and locked dependencies, runs tests, gates a separate
  accepted synthetic candidate, and asserts the degraded fixture exits exactly 1.
- Configured report upload even on failure with seven-day retention; no secrets,
  paid calls, candidate generation, pushes, or deployments are performed.
- Verified 135 tests on Python 3.12.13. YAML parsed and shell syntax checked.
- Executed the workflow replay bodies locally: accepted pass, expected regression,
  unexpected pass, and execution-error scenarios behaved correctly.
- Hosted Actions execution and artifact upload remain unverified: repository has
  not been pushed. Required branch checks must be configured later on GitHub.

## Next bounded task (not implemented)

Prepare the selected real RAG example's dataset/provenance plan: pin source and
dataset revisions, review labels and licensing, and define a small reproducible
subset before adding a recording adapter. No paid provider is required.

## Current limitations

Required-phrase, citation-ID, retrieval recall checks, a runner, gate, and reports
exist with an offline CLI, exit codes, and an unexecuted hosted CI workflow. No RAG
recording generator exists yet. Source checks use case labels, not a validated source registry.
No general semantic correctness scoring exists. Versions are manually maintained
labels, not content hashes. Configuration identity may intentionally differ between
recordings. No paid APIs or external services are used.
