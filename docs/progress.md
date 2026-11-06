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

## Next bounded task (not implemented)

Add baseline/candidate comparison and a small explicit regression gate policy.
Report generation and the CLI remain later tasks. Keep the baseline fixed.

## Current limitations

Required-phrase, citation-ID, retrieval recall checks and a runner exist; no CLI,
reports, or CI gate. Source checks use case labels, not a validated source registry.
No general semantic correctness scoring exists. Versions are manually maintained
labels, not content hashes. Configuration identity may intentionally differ between
recordings. No paid APIs or external services are used.
