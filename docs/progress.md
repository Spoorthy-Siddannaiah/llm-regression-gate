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

## Completed: recording manifest integrity validation

- Added typed local-manifest v1 validation after existing ComparisonInput checks.
- Checks completion/scope/identity/configuration, dataset/corpus hashes, and all
  listed recording/evidence hashes. Required evidence pairs must be present.
- Manifest paths stay inside the run directory, including through symlinks.
- Real digest-bearing recordings require manifests automatically; synthetic inputs
  remain supported. Added CLI `--sources` and `--require-manifests`, enabled in real CI.
- Stale inputs exit 2 before scoring/reports; the known real candidate still exits 1.
- Verified 212 offline tests and the updated real workflow command bodies locally.
- Existing recordings and manifests were not changed. No model calls, pushes, or
  hosted Actions runs. Hashes validate integrity, not signed authenticity/current PR code.

## Completed: isolated alternative-answer assertions

- Added typed `AnswerAlternatives` and `alternative-phrases-v1` results: any variant
  may match, while existing required-fact checks retain AND semantics unchanged.
- Deduplicates repeated reference annotations without inventing/splitting aliases;
  authored duplicate/blank alternatives and mismatched case IDs are errors.
- Added an offline diagnostic script validating reference coverage/source spans
  after recording provenance checks, with input hashes and a new output artifact.
- Measured real annotated-alternative coverage unchanged at baseline 0.84/candidate
  0.68. "9 miles" remains unmatched because it is not an annotated alternative.
- Verified 234 offline tests, including diagnostic reproduction and bad references.
- No model calls, dataset/recording changes, old scorer changes, or gate migration.

## Completed: optional answer-alternative report evidence

- Moved standalone diagnostic logic into shared typed models/builders; old diagnostic
  artifacts remain reproducible and matching/validation logic is reused.
- Added CLI `--answer-alternatives` and optional report API arguments. Extended reports
  use schema 2 with aggregate/per-case evidence, hashes, and diagnostic-only labels.
- Default schema-1 JSON/Markdown was checked byte-for-byte against historical output.
- Gate decisions, thresholds, metrics, and failures remain unchanged with the flag.
- Bad references exit 2 without reports; mismatch checks prevent attaching another
  recording/case set. No model calls or recording/dataset/policy changes.
- Verified 241 tests on Python 3.12.13, including both pass/fail CLI paths, old
  diagnostic reproduction, extended rendering, escaping, and non-mutation.

## Completed: optional corpus-aware citation existence

- Added `citation-existence-v1`: exact, case-sensitive lookup in the supplied corpus,
  independent of relevance labels or retrieval presence. Unknown cause is not inferred.
- Empty citations are N/A rather than a successful existence check; counts show absences.
- Added `--citation-existence` and schema-2 JSON/Markdown evidence, compatible with
  answer-alternative diagnostics. Gate decisions/policies remain unchanged.
- Measured baseline: 34 existing/1 unknown occurrences, 3 no-citation cases; candidate:
  20 existing/0 unknown occurrences, 5 no-citation cases. Saved reproducible evidence.
- Default and alternatives-only historical reports remain byte-for-byte unchanged.
- Verified 256 offline tests. No model calls or dataset/recording/policy changes.

## Completed: opt-in versioned unknown-citation enforcement

- Added explicit deterministic-gate-v2 policy with integer absolute candidate cap
  and permitted count increase; equality passes and counts represent occurrences.
- Recomputes membership against corpus input and requires corpus/hash for v2.
  No citation flag is needed to enforce the policy; missing corpus exits 2.
- Added schema-3 enforced-rule evidence/reasons without changing v1 output/defaults.
- Real baseline self-check fails unknown-ID cap (1 vs 0); top-one candidate has 0
  unknowns but still fails the three existing relative quality checks.
- Saved both policy replay results and verified 280 tests on Python 3.12.13.
- Historical default/optional reports remain byte-for-byte unchanged. No model
  calls, recording changes, policy rollout to Actions, pushes, or deployments.

## Completed: explicit v2 policy replay in CI

- Retained all v1 workflow steps and added v2 accepted-fixture, absolute-limit,
  and real-candidate relative-regression checks. No model or paid calls.
- Rejection steps require exit 1 plus the correct schema/policy, failure codes,
  and counts; a rejection for the wrong reason is not accepted as success.
- Added all six v2 report paths to always-upload artifacts (14 files total).
- Verified 280 tests, YAML parsing, shell syntax, unchanged original steps, all
  seven replay bodies, and four injected pass/error/wrong-reason scenarios locally.
- No hosted run or artifact upload was performed; nothing pushed or deployed.

## Completed: regression architecture and demo runbook

- Added `docs/architecture.md` with Mermaid flow, module boundaries, schema/policy
  versions, generation/evaluation separation, evidence, and known limitations.
- Added `docs/demo.md` with setup and verified pass, actual regression, absolute
  quality failure, and invalid-input cases (exit codes 0/1/1/2).
- Executed all documented shell blocks; reports/reasons/schema versions matched.
  Setup ran 280 passing tests. Protected data, recordings, and configs were unchanged.
- Linked docs from README and clarified actual local generation versus unverified
  hosted Actions/future fresh PR generation. No model calls, pushes, or deployment.

## Completed: future-run code provenance

- Added read-only Git revision/dirty-state capture and project-relative SHA-256
  hashes for package Python files, recorder script, pyproject, and lockfile.
- Future runs save a hashed code-provenance sidecar plus typed manifest metadata;
  source edits/additions/deletions prevent completion while preserving raw evidence.
- Missing Git metadata is explicitly unavailable, not clean or fabricated.
- Replay validates optional metadata/sidecar consistency without requiring old
  source hashes to match today's checkout. Legacy manifests remain valid unchanged.
- Verified 299 offline tests and a metadata-only local capture. No Ollama calls,
  new model recordings, changes to historical evidence, pushes, or deployment.

## Completed: opt-in candidate code freshness

- Added explicit target capture script and `--expected-candidate-code` CLI/API option.
- Requires candidate commit and full covered source hashes/file set to match the
  supplied snapshot. Git must be available; dirty state is informational.
- Baseline code is not matched to the target. Legacy replay stays valid, but a
  legacy candidate without code metadata fails an explicitly requested freshness check.
- Verified 314 tests and a local capture/legacy-rejection demo (exit 2, no reports).
  Matching metadata preserves the quality outcome and report bytes.
- No model calls, historical recording changes, pushes, or hosted execution.

## Completed: opt-in local generate-and-compare workflow

- Added `scripts/run_local_candidate.py`: preflight, expected code capture, separate
  recorder subprocess, source/input stability checks, and freshness-enforced comparison.
- Explicit policy required; existing output and output nested within baseline are
  refused. Dataset/corpus/baseline/policy/settings hashes are checked across stages.
- Preserves 0/1 quality outcomes; generation, freshness, drift, timeout, and report
  errors return 2. Completion metadata validates report identities and records hashes.
- Included wrapper code in future source snapshots; historical recordings unchanged.
- Verified 328 offline tests, including actual recorder + actual comparison CLI with
  mocked model responses for pass/fail. No real model run, paid calls, CI inference,
  baseline promotion, push, or deployment occurred.

## Completed: first actual wrapped local run

- Ran all 25 real SQuAD cases through installed local Llama 3.2, BM25 top 3,
  and `gate.citation-v2.json` using the opt-in wrapper at commit `1090676`.
- Completed with exit 1: phrase coverage .84, citation-label coverage .80, and
  Recall@3 .84 matched baseline; one unknown citation exceeded the absolute cap 0.
  This is an existing quality defect, not a newly observed aggregate regression.
- Verified all 54 baseline files unchanged, all 53 candidate artifact hashes,
  both completion report hashes, and candidate freshness against the captured target.
- Offline strict replay returned 1 and produced byte-identical JSON/Markdown reports.
  All 328 offline tests passed. Unloaded the local model after completion.
- Added `docs/local-workflow-observation.md` with measurements, hashes, and replay
  instructions. Raw evidence/reports remain local; `/runs/` is now ignored by Git.
- No paid calls, baseline promotion, hosted generation, push, or deployment.

## Completed: constrained citation request and role-aligned dataset research

- Inspected the actual failing case: its citation ID has one extra character
  compared with a retrieved source ID. Historical evidence was not edited.
- Generation requests now constrain citation items to retrieved IDs; zero hits
  allow only an empty array. Parser/evaluator still preserve and score unknown IDs.
- Versioned the changed request as `grounded-json-v2-citation-enum`, configuration
  1.1.0. Model, system text, retrieval, baseline, dataset, and policy remain fixed.
- Added tests for exact choices, the observed typo, request isolation, zero hits,
  and recorder version metadata. Actual model enforcement/quality improvement is
  not claimed; no new inference run was made in this task.
- Verified 330 passing offline tests and a clean whitespace check. Saved the
  interview question; no paid calls, baseline promotion, push, or deployment.
- Read the employer's public job-board API and primary dataset sources. Recommended
  ACI-Bench for a separate simulated clinical-documentation benchmark; documented
  license, fit, limitations, leakage boundaries, and a small adoption plan in
  `docs/voize-dataset-plan.md`. No new dataset or clinical evaluator imported.

## Completed: v0.1.0 local release preparation

- Ran the new citation-enum request on all 25 real cases: wrapper exit 0,
  unknown citation occurrences 1 → 0, with .84/.80/.84 aggregate scores unchanged.
  Only the affected case's citations changed. All 54 baseline files stayed intact.
- Verified candidate artifact and completion-report hashes, code-target freshness,
  and actual saved requests: enum choices were the only request difference.
- Preserved the actual candidate, raw evidence, manifest, and expected code target
  under `recordings/squad/llama3.2-bm25-citation-enum-v2/`; no generated reports
  committed. Added exact-evidence/integrity tests and an eighth offline CI replay.
- Verified 334 tests, all eight replay bodies and 16 reports, README quickstart,
  and five demo outcomes 0/1/1/2/0 using the installed environment. Hosted setup,
  artifact upload, and branch rules remain unverified until publication.
- Repeated all 334 tests in a clean local Git clone using installed dependencies
  and that clone's source tree. Ignored runs/reports and local untracked files
  were not needed. This was not a hosted runner or fresh dependency installation.
- Rewrote the README around the implemented release; added changelog and publication
  handoff. Code remains unlicensed at the owner's explicit choice; SQuAD retains
  its separate attribution/license notice. Clinical dataset adoption is future work.
- Local Markdown links and whitespace checks passed. Targeted scans of proposed
  files/textual Git history flagged no credential patterns; tracked/proposed files
  contained no home-directory paths or files over 10 MB. These scans are limited checks.
- GitHub authentication verified; proposed destination is the public
  `Spoorthy-Siddannaiah/llm-regression-gate`. No remote, push, or publication yet.

## Publication remains

Confirm destination/visibility before creating or pushing the repository, respecting
the current “do not push or publish” working agreement. Then verify the first hosted
Actions run and artifacts. The implemented regression-catching MVP is complete;
automatic PR inference, clinical evaluation, observability, and deployment remain
future scope rather than unfinished release requirements.

## Current limitations

Required-phrase, citation-ID, retrieval recall checks, a runner, gate, and reports
exist with an offline CLI, exit codes, local Ollama recording, and an unexecuted
hosted CI workflow. PR-driven model generation is not wired. Source checks use
case labels for relevance; the v2 gate additionally checks citation membership in
the hashed corpus. Neither establishes that a cited passage supports an answer.
No general semantic correctness scoring exists. Versions are manually maintained
labels; real manifests additionally bind files to hashes. Configuration identity
may intentionally differ between recordings. No paid APIs or hosted providers are used.

## Completed: authorized audit fixes (uncommitted)

Started at the required clean HEAD `2ad69ec05ef5697d88befe3be8bb84994f7801ae`.
The owner explicitly prohibited commits, remote configuration, publication, model
calls and adding a license; those restrictions override the earlier commit workflow.

- Phase 1: exact recorder input-byte snapshots, drift rejection before completion,
  sanitized provider errors, neutral report-origin wording. 51 focused tests passed.
- Phase 2: duplicate/nested JSON-key rejection, labelled corpus membership validation,
  paired per-case changes and optional `max_regressed_cases`. 114 focused tests passed.
  Existing thresholds/decisions are unchanged when the new limit is omitted.
- Phase 3: schema-4 evaluation receipts, verified official action SHA pins,
  Ubuntu 24.04 and pinned Python-3.12+ build dependency closure. Locked installation,
  source distribution and wheel builds passed; runtime/test uv.lock is unchanged.
- Phase 4: updated current documentation, actual report excerpt, changelog,
  publication instructions, and repeatable replay/source-snapshot helpers.
- Final verification: 356 tests passed locally and in a fresh isolated source snapshot
  with a new locked environment. All eight replay scenarios and the eight actual
  workflow replay bodies passed locally, producing all 16 report files. Five demo
  cases returned expected exits 0/1/1/2/0. Installed wheel replay passed from /tmp
  without importing the source checkout. No hosted Actions execution was performed.
- All 54 original baseline files match commit `23bb9fa`; datasets, recordings,
  benchmark artifacts, configs and original evidence are untouched. Documentation
  links, whitespace and archive exclusions passed. Targeted credential-pattern scans
  flagged no proposed-file or 407 reachable-history-blob matches; scans are limited.
- HEAD and index unchanged, no remote or license file added. Generated artifacts
  and environments remain under /tmp or ignored paths. See `docs/audit-fixes.md`.

## Remaining release actions

The repository was published after owner authorization. The first hosted CI run
failed during Python installation: uv 0.7.12 lacks a download entry for Python
3.12.13 on Linux x86_64. A local fix pins uv 0.13.7, whose catalog includes that
exact interpreter. Python, dependencies, policies and evaluation evidence remain
unchanged. The owner approved committing and pushing this fix; verify the new
hosted run and report artifacts before claiming success. Local release verification passed all
356 tests, eight replay scenarios, package builds and an isolated source snapshot.
All 54 baseline hashes matched. Semantic
correctness, representative clinical labels, privacy compliance, fresh PR inference,
latency/cost gates and production deployment remain outside this release's claims.
