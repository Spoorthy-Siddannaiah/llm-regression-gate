# Opt-in unknown-citation gate

`deterministic-gate-v2` adds corpus-membership enforcement to the existing v1
quality checks. It does not replace the default policy, change old configurations,
promote a baseline, or prove citation support. Select it explicitly with
`--policy configs/gate.citation-v2.json`.

## Two independent limits

```json
"unknown_citations": {
  "max_candidate_unknown": 0,
  "max_increase": 0
}
```

- **Absolute limit:** candidate unknown-citation occurrences must not exceed
  `max_candidate_unknown`. This can reject an unchanged candidate when the baseline
  already contains bad IDs.
- **Regression limit:** candidate count minus baseline count must not exceed
  `max_increase`. A negative change is an improvement; equality passes.

Counts are nonnegative integers. A repeated unknown ID in two requests counts as
two occurrences. IDs remain unique within each response under the existing model
contract. Existing but unlabelled sources are not unknown. Cases without citations
add zero unknown IDs; they are not evidence of citation quality, and ordinary
coverage requirements remain necessary.

V2 requires a valid corpus and its hash. The CLI loads these automatically, even
without the report-only `--citation-existence` flag. Missing or invalid corpus
inputs cause exit 2, never silent omission of enforcement. The gate recomputes
membership from the supplied observations and corpus, rather than trusting a
precomputed diagnostic attachment.

## Real replay

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.citation-v2.json \
  --output-dir reports/citation-v2-new
```

The actual top-one candidate has zero unknown IDs, so it passes the new citation
limits. It still exits 1 because the existing fact/source-coverage metrics regressed.
For the baseline self-check, set `--candidate` to the baseline recording and choose
a different output directory. That exits 1 because the unchanged baseline contains
one unknown cited ID and the absolute cap is zero; count increase is zero.

Both outcomes are saved in
[`benchmarks/squad-citation-gate-v2.json`](../benchmarks/squad-citation-gate-v2.json).
These are offline policy replays, not new generation experiments or release approval.

## Reports and compatibility

V2 uses report schema **3**, preserving the selected policy and
`citation_existence_gate` evidence: full per-case membership, corpus hash, baseline
and candidate counts, and signed count increase. Markdown labels the rule
**Enforced unknown-citation gate** and displays thresholds plus affected cases.
Failure codes distinguish `unknown_citation_limit` from `unknown_citation_increase`.
Exit 0/1/2 meanings remain unchanged.

V1 defaults and schema-1/schema-2 historical output remain unchanged. A policy file
without `policy_version` still means v1; adding unknown-citation fields to v1 is
an error. V2 requires an explicit `unknown_citations` block. Optional report flags
can coexist with v2 but cannot enable, disable, or weaken its enforcement. Any
separately supplied citation diagnostic must match the enforced evidence.

Existing v1 Actions steps are retained. Additional v2 replay steps exercise a
passing synthetic case, the baseline's absolute-limit failure, and the real
candidate's relative failures. Expected-rejection steps require exit 1 and inspect
schema/policy versions, exact failure codes, and count evidence. Wrong reasons,
unexpected passes, and execution errors fail CI. Reports from all cases are retained.
Hosted execution remains unverified; local checks passed without model calls.
An additional actual [constrained-citation candidate](../recordings/squad/llama3.2-bm25-citation-enum-v2/README.md)
now passes v2 with zero unknown IDs and unchanged aggregate scores; CI replays it
without inference and verifies its saved code target.
These tests do not adopt v2 as a required production release policy.
The example zero limits are explicit engineering
choices for demonstrating membership enforcement, not calibrated overall quality
requirements. Unknown means absent from this corpus, not proven fabrication;
membership says nothing about relevance, claim support, or truthfulness.
