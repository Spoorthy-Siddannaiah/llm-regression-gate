# Working agreement

- This is an independent LLM Reliability Platform, separate from the Databricks Enterprise AI Knowledge Copilot.
- Current scope: recorded-response regression checking plus explicitly invoked local RAG generation. No web service, database, telemetry, containers, hosted providers, or paid APIs.
- Use Python 3.12+, Pydantic, and pytest. Default to offline local datasets and recordings; never make paid API calls.
- Local Ollama generation is opt-in and separate from CI replay. Verify the installed model digest; never automatically download models or replace a baseline. Preserve raw run evidence and distinguish observations from release acceptance.
- Keep versioned datasets separate from response recordings. Use stable case IDs and explicit dataset/configuration versions.
- Reject missing cases, duplicate IDs, and incompatible comparisons. Never automatically replace the baseline.
- Deterministic fact checks are limited assertions, not proof of general semantic correctness.
- Explain purpose and trade-offs before editing. Implement one bounded task at a time, verify it, and keep teaching explanations concise.
- Maintain docs/progress.md for implementation work. Use small, meaningful local commits after verification. Remote creation and publication require explicit owner authorization. Do not add a software license without explicit authorization.
- Do not commit secrets, local environment files, or generated reports. Preserve existing work.

## Commands

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 pytest
uv run llm-reliability --help
```

Use `uv lock --python 3.12` only when intentionally updating dependencies. Preserve the runtime lock for unrelated changes. Build tools are explicitly pinned in pyproject.toml.
