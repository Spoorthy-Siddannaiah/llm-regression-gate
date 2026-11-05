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

## Next bounded task (not implemented)

Add citation source-ID checks and retrieval Recall@K with clearly defined semantics.
Comparison gates, report generation, and the CLI remain later tasks. Keep the baseline fixed.

## Current limitations

Only required-phrase presence checks exist; no runner, CLI, reports, or CI gate.
No general semantic correctness scoring exists. Versions are manually maintained
labels, not content hashes. Configuration identity may intentionally differ between
recordings. No paid APIs or external services are used.
