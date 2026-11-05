# LLM Reliability & Observability Platform

Independent portfolio project, separate from the Databricks Enterprise AI Knowledge Copilot.
Current scope: local, deterministic regression evaluation contracts only.

Target milestone: one CLI command compares recorded baseline and candidate responses
against a versioned dataset, writes JSON and Markdown reports, and exits nonzero
for a critical regression. **The CLI and scoring are not implemented yet.**

## Development

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 pytest
```

Datasets contain expectations; recordings contain observed answers and ranked retrieval
results. Pydantic validates their structure and comparison compatibility before scoring.
Configurations may differ intentionally between baseline and candidate; dataset identity,
version, and exact case coverage must match. Empty answers and unknown cited sources remain
valid observations so the future scorer can report them as quality failures.

Versions are explicit labels, not content hashes. Authors must increment versions when
changing datasets or configurations. No replay engine or full provenance verification exists yet.
Models validate on construction; callers must not mutate validated inputs in place.

The fictional support policies have no relationship to any real company's policies.
Future keyword/fact checks will test narrow assertions, not general semantic correctness.
No paid services, live providers, or automatic baseline replacement are included.
