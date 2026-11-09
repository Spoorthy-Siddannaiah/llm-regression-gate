# Actual regression report excerpt

This excerpt comes from offline replay of the committed actual top-one candidate
against the unchanged top-three baseline, using `gate.relative-only.v1.json`.
It is not a handwritten model response or an official SQuAD benchmark.

**Gate: FAIL — evaluation exit 1. Report schema: 4.**

| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| fact_coverage | 0.84 | 0.68 | -0.16 |
| citation_label_coverage | 0.80 | 0.68 | -0.12 |
| retrieval_recall | 0.84 | 0.68 | -0.16 |

Affected example: “Who was the Super Bowl 50 MVP?”

```json
{
  "case_id": "squad-56be4eafacb8001400a50302",
  "criticality": "standard",
  "metrics": [
    {
      "metric": "fact_coverage",
      "baseline": 1.0,
      "candidate": 0.0,
      "delta": -1.0
    },
    {
      "metric": "citation_label_coverage",
      "baseline": 1.0,
      "candidate": 0.0,
      "delta": -1.0
    },
    {
      "metric": "retrieval_recall",
      "baseline": 1.0,
      "candidate": 0.0,
      "delta": -1.0
    }
  ],
  "regressed_metrics": [
    "fact_coverage",
    "citation_label_coverage",
    "retrieval_recall"
  ],
  "improved_metrics": [],
  "status": "regressed",
  "critical_regression": false
}
```

The saved baseline answer is “Von Miller”; the top-one candidate returns an empty
answer. Source labels are associated paragraphs, not exhaustive relevance judgments.
The full reports contain paired changes for all 25 cases and a hash-only receipt.
No general correctness, statistical significance, latency or clinical claim follows.

Reproduce all eight known outcomes and inspect `squad-regression/report.md`:

```sh
uv run --python 3.12 --locked python scripts/verify_replays.py \
  --output-dir reports/release-replays-new
```

Use a new directory. The verification script itself returns 0 when each example
produces its expected pass/rejection; the rejected candidate still has evaluation
exit 1. See [demo](demo.md) to run individual comparisons.
