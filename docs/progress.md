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

## Completed: real-data provenance and selection plan

- Pinned the Haystack notebook commit and SHA-256 plus the dataset repository commit.
- Defined a deterministic test-shard corpus (1,000 planned rows) and 25 fixed
  evaluation rows, ID rules, duplicate handling, and manual annotation requirements.
- Added `configs/rag/pubmedqa-plan.v1.json` and `docs/pubmedqa-data-contract.md`.
- Dataset card has no declared license; materialization/redistribution remains
  pending clarification or an explicitly licensed replacement. No terms inferred.
- No corpus/model download, notebook execution, provider call, or baseline creation.
- Verified plan JSON, revision/hash formats, selection bounds, 25 unique planned
  case IDs, and no-execution flags; Git whitespace checks passed. No runtime code
  changed, so the previously passing 135-test suite was not rerun for this task.

## Completed: real online SQuAD dataset import

- User requested actual online data instead of another invented integration fixture.
- Replaced the planned PubMedQA integration with licensed SQuAD 1.1 development data.
- Downloaded the pinned official source; the importer verifies its full SHA-256.
- Materialized 25 original questions, 50 paragraphs, all answer alternatives and
  offsets, source hashes, provenance/selection manifest, and CC BY-SA attribution.
- First annotated answer is a narrow required-phrase proxy. All cases are standard;
  alternative-answer acceptance and reviewed critical labels are not implemented.
- Verified 141 tests, artifact hashes, answer offsets, source IDs, byte-for-byte
  reproduction from the real upstream file, and refusal to overwrite output.
- No generation, paid calls, or real model baseline/candidate recordings were made.

## Completed: local retrieval over real passages

- Added a typed source-corpus loader and small in-memory BM25 retriever with stable
  source-ID tie breaks, explicit settings/tokenizer versions, and no model dependencies.
- Retriever input is only question text and corpus; no facts, labels, or references.
- Added retrieval-only measurement script and committed actual rankings/input hashes.
- Measured Recall@1=0.68, Recall@3=0.84, Recall@5=0.88 on 25 questions/50 passages.
- Verified 166 tests on Python 3.12.13, including formula arithmetic, deterministic
  ranking, input validation, real-corpus retrieval, and measurement reproduction.
- Initial arithmetic test had an incorrect IDF denominator; corrected the expected
  hand calculation. The retriever formula did not require a change.
- No generated answers, citation claims, accepted model baseline, or paid calls.

## Completed: actual local generation and first observed recording

- User explicitly authorized running the baseline, so connected generation and
  recording in one bounded task. Started the local Ollama server; no model download.
- Added loopback-only schema-constrained generation with pinned installed model
  digest, prompt, seed/temperature/context/output limits, and explicit timeouts.
- Completed a one-question smoke test, then all 25 actual SQuAD questions.
- Preserved prompts/raw responses and hashes; omitted local path/tensor metadata.
- Measured phrase coverage 0.84, citation-label coverage 0.80, Recall@3 0.84.
- Reviewed four phrase failures, including a supported unit conversion, plus one
  citation ID absent from the corpus. No observations or labels were repaired.
- Recording is an observed reference, not release-approved. Self-check with
  illustrative 0.90 absolute floors fails; no relative regression claim is made.
- Verified 179 offline tests, including real recording/evidence/hash integrity.

## Completed: real candidate change and fixed-baseline comparison

- Added `--top-k` to the explicit recording script (default 3), with metadata and
  validation. Generated 25 actual candidate responses with top K changed to 1.
- Verified matching model digest, prompt/schema, options, corpus/questions, server,
  and BM25 settings. Preserved all 54 baseline files byte-for-byte.
- Relative-only comparison returned exit 1: phrase coverage 0.84 -> 0.68,
  citation-label coverage 0.80 -> 0.68, retrieval Recall@3 0.84 -> 0.68.
- Saved complete run evidence and `benchmarks/squad-top1-experiment-v1.json`.
- New real-data offline CLI replay test confirms all failures are relative drops,
  not the baseline's known failures against illustrative 0.90 absolute floors.
- Verified 187 tests on Python 3.12.13. No paid calls or automatic baseline promotion.
- One run/configuration; no statistical, semantic-accuracy, latency, or cost claim.

## Completed: explicit real-data Actions replay

- Added observed real-baseline stability replay and actual candidate expected-rejection
  steps alongside the synthetic replay cases. Both use the same relative-only policy.
- Candidate must exit exactly 1; unexpected success or execution failure breaks CI.
- Configured all eight JSON/Markdown report paths for upload even after failures.
- Verified 187 tests; workflow YAML parses and all shell blocks pass `bash -n`.
- Executed all four replay bodies locally, plus real-candidate unexpected-pass and
  missing-input scenarios. All step outcomes matched expectations. No model calls.
- No hosted Actions run or artifact upload was performed; nothing was pushed.

## Next bounded task (not implemented)

Validate real recording manifests against dataset/corpus and recording hashes before
comparison, so stale or incompatible recorded inputs fail explicitly. Automatic
PR-driven candidate generation remains separate future work.

## Current limitations

Required-phrase, citation-ID, retrieval recall checks, a runner, gate, and reports
exist with an offline CLI, exit codes, local Ollama recording, and an unexecuted
hosted CI workflow. PR-driven model generation is not wired. Source checks use
case labels, not a validated source registry.
No general semantic correctness scoring exists. Versions are manually maintained
labels, not content hashes. Configuration identity may intentionally differ between
recordings. No paid APIs or external services are used.
