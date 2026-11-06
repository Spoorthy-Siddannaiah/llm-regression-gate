# Real candidate: one retrieved passage

This recording contains 25 actual local Ollama outputs. The only intended pipeline
change from the fixed [observed baseline](../llama3.2-bm25-v1/README.md) is retrieval
depth: **three passages -> one passage**. Model digest, prompt/schema, seed,
temperature, context/output limits, server version, corpus, questions, and BM25
scoring settings are unchanged. Configuration metadata records the changed budget.
It is not synthetic failure injection. Answers and citations are preserved unchanged.

| Metric | Baseline | Candidate | Change (percentage points) |
| --- | ---: | ---: | ---: |
| Required-phrase coverage | 84% | 68% | -16 |
| Citation-label coverage | 80% | 68% | -12 |
| Recall@3 | 84% | 68% | -16 |

Both sides use the same evaluator with K=3. The candidate emits only one source,
so its Recall@3 is limited to that one-source result set. This demonstrates lost
coverage from a smaller context budget, not worse BM25 ranking. Five questions
lose a passing first-answer phrase and one gains it; the net change is four cases.

Example: "Who was the Super Bowl 50 MVP?" Baseline answers "Von Miller"; the
candidate omits the associated source from retrieval and returns an empty answer.
The correct behaviour of abstaining when evidence is missing still represents
lost end-to-end answer coverage after the pipeline change.

The **relative-only** policy has zero aggregate floors and permits no drops, so
all three measured drops fail the gate (exit 1). This isolates regressions from
the baseline's pre-existing failures against illustrative 90% floors. Relative-only
passing would not establish release quality. No baseline was replaced or promoted.

## Replay without Ollama

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/squad/v1/dataset.json \
  --baseline recordings/squad/llama3.2-bm25-v1/recording.json \
  --candidate recordings/squad/llama3.2-bm25-top1-v1/recording.json \
  --policy configs/gate.relative-only.v1.json \
  --settings configs/evaluator.v1.json \
  --output-dir reports/squad-top1-replay-new
```

Expected exit: 1, with JSON and Markdown reports. Choose a new output directory.
For a new actual generation run, use `scripts/record_ollama.py --top-k 1` with a
new recording ID/directory and the same dataset/sources arguments. This makes
local model calls and is separate from offline replay.

Full prompts, raw outputs, settings, hashes, and timestamps are preserved here.
See [comparison artifact](../../../benchmarks/squad-top1-experiment-v1.json).
This is one small run per configuration, not a statistical estimate or a controlled
latency/cost improvement study. Temperature zero does not guarantee regeneration
determinism. First-span matching and nonexhaustive source-label limitations remain.

Requests reproduce [SQuAD-derived text under CC BY-SA 4.0](../../../datasets/squad/v1/README.md).
Attribution is in that dataset README. Model license metadata is retained in the
manifest; no model weights are redistributed.
