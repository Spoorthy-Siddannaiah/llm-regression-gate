# LLM Reliability & Observability Platform

Independent portfolio project, separate from the Databricks Enterprise AI Knowledge Copilot.
Current scope: typed contracts, synthetic recordings, validated loading, and required-phrase checks.

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

## Loading local inputs

```python
from llm_reliability.loading import load_comparison

comparison = load_comparison(
    "datasets/support_policy/v1/dataset.json",
    "recordings/baseline.synthetic.v1.json",
    "recordings/candidate.synthetic.v2.json",
)
```

Paths are relative to the current working directory; this example runs from the
repository root. Individual `load_dataset` and `load_recording` functions also exist.
Files are read as UTF-8, validated using their Pydantic models, and then checked
together through `ComparisonInput`. `InputLoadError` identifies the input paths
and validation details without dumping entire response payloads.

Both recordings are handwritten synthetic fixtures, not model outputs. The
candidate deliberately gives an incorrect refund window and omits a required fact.
Loading validates input structure and compatibility, not answer quality. Files are
never written or used to replace the baseline by the loader.

## Required-fact checks

`check_required_facts(case, response)` in `llm_reliability.fact_checks` returns
the original required phrases partitioned into `matched_facts` and `missing_facts`.
`all_required_facts_present` means only that no required phrases were missing.
The function rejects mismatched case IDs and leaves inputs unchanged.

Matching uses case folding and whitespace normalization, literal punctuation, and
word boundaries at either end (so `130 days` does not satisfy `30 days`). It does
not understand negation or paraphrases and cannot establish semantic correctness.
The synthetic candidate refund answer misses `30 days` and `proof of purchase`;
no gate decision or report is generated yet.

The fictional support policies have no relationship to any real company's policies.
These phrase checks test narrow assertions, not general semantic correctness.
No paid services, live providers, or automatic baseline replacement are included.
