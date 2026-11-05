# Working agreement

- This is an independent LLM Reliability Platform, separate from the Databricks Enterprise AI Knowledge Copilot.
- Current scope: recorded-response regression checking only. No web service, database, telemetry, containers, live providers, or paid APIs.
- Use Python 3.12+, Pydantic, and pytest. Default to local fixtures; never make paid API calls.
- Keep versioned datasets separate from response recordings. Use stable case IDs and explicit dataset/configuration versions.
- Reject missing cases, duplicate IDs, and incompatible comparisons. Never automatically replace the baseline.
- Deterministic fact checks are limited assertions, not proof of general semantic correctness.
- Explain purpose and trade-offs before editing. Implement one bounded task per turn; verify, explain the code, and ask one practical interview question. Stop before the next task.
- Maintain docs/progress.md. Make small meaningful Git commits after verification; do not push or publish.
- Do not commit secrets, local environment files, or generated reports. Preserve existing work.

## Commands

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 pytest
```

Use `uv lock --python 3.12` when intentionally updating dependencies; commit uv.lock.
