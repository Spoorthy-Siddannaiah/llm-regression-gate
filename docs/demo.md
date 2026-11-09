# Offline regression demo

Run from the repository root in the same interactive shell. No Ollama server,
provider key, model download, or paid inference is needed. Initial dependency
installation may need internet access. Every command writes to a new directory.
The original four cases and the constrained-citation replay below are verified
locally. Hosted Actions execution and deployment remain separate.

## Setup

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 --locked pytest
LLM_DEMO_DIR="$(mktemp -d /tmp/llm-reliability-demo.XXXXXX)"
echo "Demo reports: $LLM_DEMO_DIR"
```

The following blocks print the CLI's exit status. Nonzero results are intentional;
run interactively rather than under shell `set -e`. CI handles expected rejections
explicitly and inspects their reason; a release gate must not ignore failed checks.

## 1. Show a passing contract check

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/support_policy/v1/dataset.json \
  --baseline recordings/baseline.synthetic.v1.json \
  --candidate recordings/candidate.synthetic.v1.json \
  --policy configs/gate.citation-v2.json \
  --settings configs/evaluator.v1.json \
  --output-dir "$LLM_DEMO_DIR/pass"
echo "exit=$?"
```

Expected: **exit 0**, `PASS`, schema-4 reports. This is a synthetic fixture proving
the passing path, not a model-quality benchmark.

## 2. Catch an actual RAG regression

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.relative-only.v1.json \
  --settings configs/evaluator.v1.json \
  --answer-alternatives datasets/squad/v1/references.json \
  --citation-existence \
  --output-dir "$LLM_DEMO_DIR/regression"
echo "exit=$?"
```

Expected: **exit 1**, three `excessive_drop` failures, schema-4 reports. Open
`$LLM_DEMO_DIR/regression/report.md`. Show:

| Metric | Baseline: top 3 | Candidate: top 1 |
| --- | ---: | ---: |
| Required-phrase coverage | 84% | 68% |
| Citation-label coverage | 80% | 68% |
| Recall@3 | 84% | 68% |

For “Who was the Super Bowl 50 MVP?”, the baseline answers “Von Miller”; the
candidate loses the associated passage and returns an empty answer. Model digest,
prompt, generation settings, dataset/corpus, and BM25 settings match. This is a
coverage loss from a smaller passage budget, not degraded BM25 ranking.

Optional sections show answer alternatives and unknown citations without changing
the v1 gate. Baseline unknown count is 1; candidate unknown count is 0. Having fewer
unknown IDs does not erase the candidate's other quality regressions.

## 3. Separate absolute quality from regression

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-v1/recording.json \
  --policy configs/gate.citation-v2.json \
  --settings configs/evaluator.v1.json \
  --output-dir "$LLM_DEMO_DIR/absolute-quality"
echo "exit=$?"
```

Expected: **exit 1**, `unknown_citation_limit`, schema-4 reports. The candidate is
the same recording as the baseline: increase is 0, but the absolute cap is 0 and
one unknown ID exists. This demonstrates why an unchanged bad baseline cannot
establish release quality. It is a self-check, not a new candidate experiment.

## 4. Show a broken evaluation input

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/does-not-exist.json \
  --policy configs/gate.citation-v2.json \
  --output-dir "$LLM_DEMO_DIR/execution-error"
echo "exit=$?"
```

Expected: **exit 2**, an error naming the missing file, and no report directory.
The evaluator cannot make a trustworthy quality decision from invalid inputs.

## 5. Replay the actual controlled fix

```sh
uv run --python 3.12 --locked llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --sources datasets/squad/v1/sources.json --require-manifests \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-citation-enum-v2/recording.json \
  --expected-candidate-code recordings/squad/llama3.2-bm25-citation-enum-v2/expected-code.json \
  --policy configs/gate.citation-v2.json \
  --settings configs/evaluator.v1.json \
  --output-dir "$LLM_DEMO_DIR/controlled-fix"
echo "exit=$?"
```

Expected: **exit 0**, schema-4 reports. Unknown citations fall from 1 to 0 with
unchanged .84/.80/.84 aggregate metrics. The new generator's citation enum is
the only saved request difference; neither baseline nor policy was changed.
The saved expected-code target verifies historical provenance, not current-PR inference.

## Explain the result in an interview

“I built a versioned recorded-response evaluator and release gate. A real local
RAG change reduced the passage budget and produced measurable regressions, which
the CLI rejected with case-level evidence. Separate absolute rules catch an
already-bad reference. Provenance errors fail before scoring. CI replays the
known cases, but fresh PR-driven model generation and hosted verification remain
future work.”

Be explicit: the reference is observed, not release-approved; phrase/source checks
are limited assertions, not semantic correctness. The small SQuAD slice and one
run per configuration do not establish generalization or statistical significance.
No deployment or live monitoring is implemented. Read [architecture](architecture.md)
and [limitations of the v2 policy](citation-gate-v2.md) for details.
