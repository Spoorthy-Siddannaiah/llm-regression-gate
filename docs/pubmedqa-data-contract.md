# PubMedQA preparation contract

This is a plan, not an imported dataset, runnable RAG configuration, or measured
baseline. The machine-readable companion is
[`configs/rag/pubmedqa-plan.v1.json`](../configs/rag/pubmedqa-plan.v1.json).
It is not accepted by the CLI's `--settings` option.

## Verified sources

- [Pinned tutorial notebook](https://github.com/deepset-ai/haystack-tutorials/blob/61213e2a8664e5137e9cc73d24d7458ae1ba0808/tutorials/35_Evaluating_RAG_Pipelines.ipynb)
  was inspected without execution. Its SHA-256 is in the plan. It uses OpenAI
  generation and random question sampling, so we will adapt both behaviours.
- [Pinned dataset card](https://huggingface.co/datasets/vblagoje/PubMedQA_instruction/blob/2cd0ea2038adc766d6a71f37b278f9861418e9a2/README.md)
  declares instruction/context/response/category strings and 1,000 test rows.
  It declares no dataset license. The tutorial repository's Apache-2.0 code license
  does not establish the data's license. Data use/redistribution terms remain
  unresolved; no corpus text has been downloaded or committed in this step.

## Fixed selection

Use all 1,000 rows of the pinned **test** Parquet file as the candidate corpus,
and rows 0–24 as the 25 evaluation questions. This intentionally differs from the
tutorial's first 1,000 training rows and random sample. A small test shard avoids
requiring the much larger training file. This is an engineering integration slice,
not a representative medical benchmark or an official tutorial score reproduction.

Use physical file row order; do not shuffle or query an unpinned viewer endpoint.
Require the expected fields, row count, and nonblank strings. Fail on malformed
rows or repeated normalized questions (case-folded with whitespace collapsed),
rather than silently replacing cases to improve scores. A new selection needs a
new plan/dataset version.

Case IDs use the original zero-based row index, for example `pubmedqa-test-r0000`.
Source IDs use the full SHA-256 of the exact UTF-8 context string. Identical contexts
deduplicate into a single document; retain all row-to-document mappings. Do not
normalize source text before hashing. Hash and record the downloaded file and the
materialized outputs before treating the dataset as reproducible. Those hashes
are not yet available because the data file has not been downloaded.

Retrieve from the entire selected corpus, not just each question's associated
context. Only context text enters retrieval; reference answers and case labels
must not enter the prompt or corpus. Do not assume the upstream context is the
only relevant source: these are associated-context labels, not exhaustive qrels.

## Annotation and recording boundary

The upstream response is a reference answer, not a required phrase list and not
our pipeline's baseline output. Preserve it in a separate reference artifact.
Manually review short required-fact assertions against the context/reference pair
and choose criticality with a written rationale. Do not automatically mark every
medical question critical or require the entire reference answer as an exact phrase.
Until annotations exist, this plan cannot be loaded as our `Dataset` model.

A later adapter will materialize the existing `Dataset` contract plus source and
reference artifacts. A separate pipeline job will generate a `Recording` containing
actual answers, emitted citation IDs, and ranked retrieved IDs. Missing citations
must stay missing; never manufacture citations from the relevance labels.

Create the baseline from that pipeline run and review it independently of the
candidate. Record model revision, prompt/retrieval versions, corpus identity,
generation settings, and recording provenance in a sidecar manifest. Our current
models do not yet capture all of this provenance. A model's prior exposure to the
benchmark cannot be excluded; avoid claiming unseen-data generalization.

CI will replay recordings without model calls. Generating a fresh candidate from
PR changes is a later integration step, not functionality delivered here.

## Next implementation boundary

Build a local-file adapter with tiny invented rows as tests, preserving the existing
evaluator contracts. Do not bundle PubMed text while terms are unresolved. Resolve
the data terms or choose an explicitly licensed replacement before materializing
the public dataset. Local generator choice and hardware verification remain later.
