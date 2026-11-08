# LLM Reliability & Observability Platform

Independent portfolio project, separate from the Databricks Enterprise AI Knowledge Copilot.
Current scope: offline regression evaluation, opt-in local RAG recording, manifest
integrity checks, versioned policies, reports, and configured CI replay.

The first local milestone is implemented: one CLI command compares recorded baseline
and candidate responses against a versioned dataset, writes JSON and Markdown
reports, and exits nonzero for a critical regression. A GitHub Actions workflow
is included. Actual local RAG runs are recorded; hosted Actions execution and fresh
PR-driven candidate generation remain unverified/unimplemented, respectively.

Start with the [architecture](docs/architecture.md) and [offline demo runbook](docs/demo.md).

## Development

```sh
uv sync --python 3.12 --locked
uv run --python 3.12 pytest
```

Datasets contain expectations; recordings contain observed answers and ranked retrieval
results. Pydantic validates their structure and comparison compatibility before scoring.
Configurations may differ intentionally between baseline and candidate; dataset identity,
version, and exact case coverage must match. Empty answers and unknown cited sources remain
valid observations for quality checks; malformed or incompatible inputs stop evaluation.

Versions are explicit labels. Authors must increment them when changing datasets
or configurations. Real recording manifests now bind dataset/corpus and recording
artifacts to byte hashes; this is integrity validation, not signed provenance.
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

An isolated [alternative-answer diagnostic](docs/answer-alternatives.md) now
supports **any one** explicitly listed answer phrase, separately from required
facts which still require **all** phrases. It does not change `deterministic-v1`
gates. On the real recordings, annotated-alternative coverage remains 0.84 for the
baseline and 0.68 for the candidate. It is not semantic correctness scoring.
Pass `--answer-alternatives datasets/squad/v1/references.json` to the real comparison
command to include per-case evidence in JSON and Markdown. This opt-in uses report
schema 2; without it, schema 1 output is unchanged. Gate outcomes stay identical.

`check_required_facts(case, response)` in `llm_reliability.fact_checks` returns
the original required phrases partitioned into `matched_facts` and `missing_facts`.
`all_required_facts_present` means only that no required phrases were missing.
The function rejects mismatched case IDs and leaves inputs unchanged.

Matching uses case folding and whitespace normalization, literal punctuation, and
word boundaries at either end (so `130 days` does not satisfy `30 days`). It does
not understand negation or paraphrases and cannot establish semantic correctness.
The synthetic candidate refund answer misses `30 days` and `proof of purchase`;
no gate decision or report is generated yet.

## Citation IDs and retrieval

An optional [corpus-aware existence diagnostic](docs/citation-existence.md) is now
available via `--citation-existence`. It distinguishes cited IDs present in the
supplied corpus from unknown IDs, independently of relevance labels. It reports
no-citation cases separately and does not affect the gate. Real baseline/candidate
unknown counts are 1/0; fewer unknown IDs do not override other regressions.

`check_citation_ids(case, response)` in `llm_reliability.source_checks` lists cited
IDs labelled relevant for the case, cited IDs without relevance labels, and relevant
IDs not cited. An unlabelled ID might exist and might be useful; this check does not
validate it against a complete corpus. A matching ID does not prove citation support,
and missing a labelled source is evidence for review, not an automatic gate decision.

`check_retrieval_recall(case, response, k=3)` returns the ranked top-K IDs, found
and missing relevant IDs, and a `recall_at_k` property:

```text
Recall@K = relevant source IDs in top K / all labelled relevant source IDs
```

K must be a positive integer; booleans are rejected. Empty retrieval gives zero
recall. A short result list uses the same denominator. Dataset/response contracts
already require nonempty relevance labels and unique retrieval IDs. IDs must use
the same granularity (documents or chunks) on both sides.

Both synthetic recordings have Recall@1 = 1.0 and cite their labelled sources.
The candidate's wrong answer illustrates why these checks cannot replace answer
evaluation. Computed recall is accessed as a Python property; report serialization
is a later task.

## Evaluation runner

```python
from llm_reliability.runner import EvaluationSettings, evaluate_comparison

result = evaluate_comparison(
    comparison, settings=EvaluationSettings(retrieval_k=1)
)
refund = result.candidate.cases[0]
print(refund.required_facts.missing_facts)
# ('30 days', 'proof of purchase')
```

The runner consumes the validated comparison loaded above and joins responses by
case ID in dataset order. It applies identical evaluator settings to both sides.
Results retain dataset identity/schema/version, recording IDs, model/prompt/retrieval
configuration snapshots, case criticality, and evaluator settings/version.
Computed phrase-presence and recall values are included in `result.model_dump()`.
Inputs must remain unmodified after validation, as with the existing contracts.
The runner does not write files, aggregate scores, decide release eligibility, or
replace the baseline. Result models are output contracts; parsing serialized results
back into models is not yet supported as a persistence API.

The active real-data integration uses an imported
[SQuAD 1.1 development slice](datasets/squad/v1/README.md): 25 real questions,
50 source paragraphs, original reference answers, and pinned provenance. This
replaces the unmaterialized PubMedQA plan. A first real local recording is now
available as an observed reference; it is not release-approved.

The offline importer `scripts/prepare_squad.py` verifies the full upstream checksum
and reproduces the committed subset. Data attribution and CC BY-SA 4.0 license
information are in the dataset README. Unit/regression tests keep their existing
synthetic fixtures; integration data now comes from the actual public dataset.

## Local retrieval

```python
from llm_reliability.loading import load_corpus
from llm_reliability.retrieval import BM25Retriever

retriever = BM25Retriever(load_corpus("datasets/squad/v1/sources.json"))
hits = retriever.retrieve("Which NFL team represented the AFC at Super Bowl 50?", top_k=3)
for hit in hits:
    print(hit.source_id, hit.score)
```

The in-memory retriever accepts only questions and corpus text. It returns ranked
source IDs, paragraph text, and BM25 scores. It has no access to reference answers,
required facts, or relevance labels. Corpus text is snapshotted; validated inputs
must not be mutated before constructing the retriever. Empty or unmatched queries
return no hits. K must be a positive integer. Ties sort by source ID.

BM25 is a lexical baseline suitable for this 50-passage local example. It does
not handle synonyms semantically; the implementation scans all paragraphs and
is not intended as a large production search engine. No vector store, model
download, or paid API is needed. Tokenizer and k1/b settings are explicit/versioned.

Measured on the real slice: Recall@1 **0.68**, Recall@3 **0.84**, Recall@5 **0.88**.
See [benchmark evidence and reproduction](benchmarks/README.md). These are retrieval
measurements only; the separate local model run is documented below.

## First real local model recording

The [observed baseline recording](recordings/squad/llama3.2-bm25-v1/README.md) contains
25 actual answers from the installed Llama 3.2 3B model through local Ollama and BM25
top-3 retrieval. It includes exact prompts, raw responses, model digest, options,
and input/artifact hashes. Reference answers never enter generation prompts.

Measured required-phrase coverage is **0.84**, citation-label coverage **0.80**,
and Recall@3 **0.84**. This is a completed observed run, not an accepted production
baseline. One supported unit conversion is missed by the phrase check; real answer
and citation failures also exist. A self-check against illustrative 0.90 floors
fails. No candidate comparison or improvement claim is made by that self-check.

See [local generation](docs/local-generation.md) for explicit opt-in recording.
`scripts/record_ollama.py` is separate from offline CI replay, refuses existing
output directories, verifies the installed digest, and never downloads models or
automatically replaces baselines. CI replays both synthetic fixtures and real
recordings, and checks their integrity without Ollama.
Future recordings also include Git revision/dirty-state metadata and source/config
hashes, with a drift check before completion. Existing recordings are not backfilled.
See [code provenance details](docs/local-generation.md#code-provenance-for-future-recordings).

## Real candidate regression caught

A separate [actual candidate run](recordings/squad/llama3.2-bm25-top1-v1/README.md)
changes only the intended retrieval budget from three passages to one. Model,
prompt, generation settings, questions/corpus, and BM25 settings match; all 54
baseline files remain unchanged. The relative-only gate returns **exit 1**:

| Metric | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| Required-phrase coverage | 84% | 68% | -16 percentage points |
| Citation-label coverage | 80% | 68% | -12 percentage points |
| Recall@3 | 84% | 68% | -16 percentage points |

For "Who was the Super Bowl 50 MVP?", the baseline answers "Von Miller";
the candidate does not retrieve its associated passage and returns an empty answer.
The evidence is in [the experiment artifact](benchmarks/squad-top1-experiment-v1.json).

`configs/gate.relative-only.v1.json` uses zero metric floors and permits no drops.
It isolates relative regressions rather than re-reporting the baseline's known
absolute-quality failures. Passing that policy would not establish production
acceptance. This is a small single-run experiment with limited phrase/source-ID
checks, not a semantic-accuracy, statistical, latency, or cost benchmark.
Both pytest and explicit Actions steps replay the real comparison CLI offline.
No model calls are added to CI.

## Comparison and gate policy

An explicitly selected [v2 policy](docs/citation-gate-v2.md) can now enforce maximum
candidate unknown-citation counts and maximum increases from baseline. V1 remains
the default. V2 automatically requires corpus evidence and writes schema-3 reports;
report-only diagnostic flags do not enable or disable this rule.

```python
from llm_reliability.gates import GatePolicy, MetricThreshold, compare_and_gate

decision = compare_and_gate(
    comparison,
    policy=GatePolicy(fact_coverage=MetricThreshold(minimum=0.9, max_drop=0.02)),
)
print(decision.passed)  # False for the synthetic candidate
for failure in decision.failures:
    print(failure.code, failure.case_id, failure.message)
```

`compare_and_gate` calls the runner with shared settings, retains its detailed
evaluation, and returns three mean metric comparisons with candidate-minus-baseline
deltas. Each case has equal weight:

- Fact coverage: matched required phrases / all required phrases, averaged over cases.
- Citation-label coverage: relevant cited IDs / all labelled relevant IDs, averaged
  over cases. Extra unlabelled citations remain in the detailed results and are not
  penalized by this metric. This is not citation precision or semantic support.
- Retrieval recall: mean per-case Recall@K.

Each metric has a candidate `minimum` and an allowed absolute `max_drop` in [0, 1].
A drop of 0.02 means two percentage points, not two percent relative to baseline.
Equality passes; comparisons tolerate floating-point noise up to 1e-12. Thresholds
must be finite. Defaults use minimum 0.0 and max_drop 0.0 for every metric.

Independently, `require_critical_facts=True` rejects any critical candidate case
with missing required phrases, even if its baseline also failed. Aggregate gains
cannot override this rule. Setting it false is an explicit policy relaxation and
is recorded in the result. Standard-case losses can be offset by other gains in
the mean; general per-case regression policies are not implemented.

Policy identity and values are preserved in the decision. These settings govern
narrow assertions, not general correctness. The gate returns a Python result only;
A GitHub Actions replay workflow is included. The baseline is
never replaced automatically.

## Reports

```python
from llm_reliability.reports import render_json, render_markdown, write_reports

json_text = render_json(decision)
markdown_text = render_markdown(decision)
json_path, markdown_path = write_reports(decision, "reports/my-run-001")
```

Default JSON contains report schema version 1 plus the complete gate result, including
computed metrics, configuration snapshots, evaluator settings, and policy. It is
an output artifact, not a supported input format for the existing result models.
Markdown presents the decision, aggregate changes, thresholds, gate failures, and
per-case evidence for both recordings. Fixture text is escaped. Displayed numbers
are rounded to six decimals; JSON preserves numeric values.

Rendering is deterministic and does not write files. `write_reports` writes UTF-8
`report.json` and `report.md` in a new directory, refusing existing destinations.
The pair is not atomic: an I/O failure can leave partial artifacts. `ReportWriteError`
names the destination; inspect partial output and retry with a new directory.
Generated `reports/` artifacts are excluded from Git. Reports do not promote baselines.

A real baseline must be deliberately recorded, reviewed, and accepted with pinned
data and configuration. It can have known weaknesses, so use absolute candidate
floors as well as relative regression limits. The support-policy fixture baseline
is synthetic. The separate real SQuAD reference has measured results and known
failures; it is not release-approved.

## Offline CLI

After `uv sync --python 3.12 --locked`, run from the repository root:

```sh
uv run --python 3.12 llm-reliability \
  --dataset datasets/support_policy/v1/dataset.json \
  --baseline recordings/baseline.synthetic.v1.json \
  --candidate recordings/candidate.synthetic.v2.json \
  --policy configs/gate.synthetic.v1.json \
  --settings configs/evaluator.v1.json \
  --output-dir reports/cli-run-001
```

This deliberately failing synthetic example writes both reports and exits **1**.
For a passing smoke test, use the baseline file as both baseline and candidate,
and select a new output directory. That smoke test is not evidence of an improved
pipeline. Each invocation needs a new output directory; output is never overwritten.

| Exit code | Meaning | Reports |
| --- | --- | --- |
| 0 | Quality gate passed | JSON and Markdown written |
| 1 | Quality gate failed | JSON and Markdown written |
| 2 | Invalid arguments/inputs or execution failure | May be absent or partial |

An output failure takes precedence over a gate decision and returns 2. Expected
input/output errors identify the file/directory. Unexpected errors report the
exception type without dumping response payloads; deeper debugging requires Python
development tools. `--help` exits 0; missing required arguments exit 2.
`python -m llm_reliability` and `python -m llm_reliability.cli` use the same CLI.
`--policy` and `--settings` are optional; omitting them uses model defaults (including
zero metric floors). The example's 0.9 floors are illustrative synthetic settings,
not calibrated production requirements. Effective values are preserved in reports.

For real recordings, manifests are checked before scoring. Supply `--sources`
and `--require-manifests` explicitly in CI. Otherwise manifests are auto-detected
beside recordings, and digest-bearing model versions still require them even if
sidecars are missing. The default corpus path is `sources.json` beside the dataset.
Stale dataset/corpus bytes, changed recording/evidence, incomplete metadata, or
configuration mismatches produce **exit 2 before reports**, not a quality failure.
Synthetic fixtures without manifests retain their original behaviour.
See [provenance checks and a complete command](docs/provenance.md).

## How a RAG team would use it

1. Review a versioned test dataset and record an accepted pipeline's outputs as
   the baseline. Review labels and critical cases; choose meaningful thresholds.
2. A developer changes a prompt, retriever, reranker, model, or chunking setting.
3. A recording job runs that candidate on the same questions/corpus snapshot and
   writes answers, citations, ranked retrieval IDs, and configuration versions.
4. CI invokes this CLI. Exit 0 permits the quality check to pass; exits 1 and 2
   block it, distinguishing a quality failure from a broken evaluation run.
5. Review report evidence, fix the change, and rerun. Any baseline promotion is a
   separate deliberate review action; never automatically promote candidate output.

For example, reducing retrieval from five chunks to one might omit a refund-policy
document and cause the answer to omit proof of purchase. Retrieval and phrase checks
help distinguish where the failure appeared. A metric change alone does not prove
its cause. This is pre-release testing, not live traffic monitoring, and passing
these narrow checks is not proof of general semantic correctness.

Our comparison command consumes recordings only. Local RAG recording is a separate
explicit script; automatic PR candidate generation remains future work. Replay
never makes model calls.

## GitHub Actions

[Regression workflow](.github/workflows/regression.yml) runs on pull requests,
pushes, and manual dispatch. It installs Python 3.12.13 and dependencies from
`uv.lock`, then runs:

1. The pytest suite.
2. The actual CLI gate on `candidate.synthetic.v1.json`, the accepted synthetic
   fixture. A quality failure (1) or execution error (2) fails this step.
3. A separate negative check on `candidate.synthetic.v2.json`. It must return
   exactly 1; an unexpected pass or execution error fails this check.
4. Self-replay of the observed real SQuAD baseline under the relative-only policy.
   This must pass as a stability check; it does not approve the baseline's quality.
5. Replay of the actual top-one SQuAD candidate against that fixed baseline.
   It must return exactly 1; an unexpected pass or execution error fails the step.
6. The accepted synthetic candidate under v2 must pass with zero unknown IDs.
7. The real baseline self-check under v2 must fail specifically with
   `unknown_citation_limit`, count 1, and increase 0.
8. The real top-one candidate under v2 must fail specifically on the three prior
   relative metrics, with zero unknown IDs and count change -1.

Replay steps still run after test failures when installation succeeded. The
workflow never suppresses the accepted gate's failure. Available reports from
all seven evaluations (14 files) are uploaded as `regression-reports` with seven-day retention,
even when earlier checks fail. Setup failures may produce no reports.

The workflow uses read-only repository permissions, no persisted checkout
credentials, and no model-provider secrets or paid inference calls. Runner and
dependency setup still require network access. The synthetic accepted candidate
is handwritten. The real candidate contains actual previously recorded outputs
from the changed RAG pipeline, not freshly generated responses to each PR's code.
The baseline is not automatically promoted. Changes to baseline fixtures and
thresholds still require deliberate review; this workflow does not enforce
approval or protect baseline contents from edits in a pull request.

Local verification covered YAML parsing, shell syntax, replay step execution
(including unexpected-pass/error/wrong-failure-reason scenarios), and 280 passing tests. No hosted
Actions run or artifact upload has been verified; nothing has been pushed.
After publishing, select `Tests and recorded-response gate` as a required status
check in GitHub branch protection/rulesets to prevent merging failed checks.
This workflow does not deploy anything.

V2 checks inspect the report's policy/schema versions, failure codes, and enforced
counts after checking exit 1. Rejecting a case for the wrong reason is a test failure.
Existing v1 replay steps remain unchanged. These are policy-behaviour tests over
known recordings, not approval of the observed baseline for production.

A green workflow means the evaluator passed its tests and correctly accepted or
rejected these known recordings. It does not mean the intentionally degraded
candidate passed, nor does it approve deployment. Automatic candidate generation
from a PR's model/prompt/retrieval changes is not wired yet.

Action usage follows the upstream documentation for
[checkout](https://github.com/actions/checkout),
[setup-uv](https://github.com/astral-sh/setup-uv), and
[upload-artifact](https://github.com/actions/upload-artifact).

The fictional support policies have no relationship to any real company's policies.
These phrase checks test narrow assertions, not general semantic correctness.
No paid services, live providers, or automatic baseline replacement are included.
