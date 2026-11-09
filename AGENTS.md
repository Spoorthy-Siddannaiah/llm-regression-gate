# Working agreement

- This is an independent LLM Reliability Platform, separate from the Databricks Enterprise AI Knowledge Copilot.
- Current scope: recorded-response regression checking plus explicitly invoked local RAG generation. No web service, database, telemetry, containers, hosted providers, or paid APIs.
- Use Python 3.12+, Pydantic, and pytest. Default to offline local datasets and recordings; never make paid API calls.
- Local Ollama generation is opt-in and separate from CI replay. Verify the installed model digest; never automatically download models or replace a baseline. Preserve raw run evidence and distinguish observations from release acceptance.
- Keep versioned datasets separate from response recordings. Use stable case IDs and explicit dataset/configuration versions.
- Reject missing cases, duplicate IDs, and incompatible comparisons. Never automatically replace the baseline.
- Deterministic fact checks are limited assertions, not proof of general semantic correctness.
- Explain purpose and trade-offs before editing. For the authorized audit-fix task, implement and verify each phase before proceeding; keep teaching explanations concise.
- Maintain docs/progress.md. Current authorization forbids commits, remotes, pushes, publication, and adding a software license. Leave verified changes uncommitted for review.
- Do not commit secrets, local environment files, or generated reports. Preserve existing work.

## Commands

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 pytest
uv run llm-reliability --help
```

Use `uv lock --python 3.12` only when intentionally updating dependencies. Keep the runtime lock unchanged for these audit fixes. Build tools are explicitly pinned in pyproject.toml.
