# Selected real-data integration: SQuAD 1.1

## Active decision

Use the real [SQuAD 1.1 development slice](../datasets/squad/v1/README.md) now
committed under `datasets/squad/v1`: 25 original questions, 50 context paragraphs,
reference answer spans, attribution, and checksums. It has a declared CC BY-SA 4.0
license and stable upstream IDs. This supersedes the unmaterialized PubMedQA plan.

The pinned source is imported by `scripts/prepare_squad.py`; tests verify the real
artifacts offline. No generated baseline exists. A later local retrieval/generation
adapter will consume only questions and corpus text, keeping reference answers
out of retrieval and prompts. The existing synthetic cases remain unit-test and
failure-injection examples, not the real integration dataset.

SQuAD is extractive QA data being adapted for a RAG integration slice, not an
already-built RAG pipeline or a source of baseline model results. The Haystack
tutorial below remains an architecture reference; its PubMedQA data choice is
superseded. Required-phrase checking currently accepts only the first answer span;
alternative-answer evaluation needs a later explicit extension.

## Historical selection: Haystack + PubMedQA (superseded)

Decision: adapt Haystack's official [Evaluating RAG Pipelines tutorial](https://haystack.deepset.ai/tutorials/35_evaluating_rag_pipelines).
Selected on 2026-11-06; integration is not implemented.

The source revisions and selection rules are now pinned in
[pubmedqa-data-contract.md](pubmedqa-data-contract.md). The dataset card does not
declare a license, so the tutorial remains our architecture reference while dataset
materialization is pending clarification or an explicitly licensed replacement.
This limitation was discovered during provenance inspection, after selection.

## Why this fits

The tutorial builds an actual retrieval-and-generation pipeline using an in-memory
document store and embedding retrieval. It uses `vblagoje/PubMedQA_instruction`,
which pairs questions with contexts and reference answers. This gives us a concrete
starting point for source labels, reference answers, and recorded pipeline outputs.
An official, inspectable example is easier to explain and reproduce than borrowing
an arbitrary project's headline evaluation scores.

This is our best fit among the examples reviewed for end-to-end RAG integration,
not a claim that PubMedQA is the best benchmark for every application. BEIR is
valuable for retrieval-only benchmarks, but does not itself provide the full
answer-generation example we want here.

## Adaptation plan, after the local regression gate works

- Pin the tutorial revision, dataset revision, document IDs, corpus selection,
  and a fixed set of roughly 25 questions. Preserve the corpus as distractors;
  do not retrieve only from each question's known supporting document.
- Review labels and answer expectations. Context-derived source labels are not
  necessarily exhaustive relevance judgments across the corpus.
- Create our own baseline recordings with pinned model, prompt, and retrieval
  settings. Published tutorial results are not our reproducible baseline.
- The tutorial uses OpenAI generation and an API key. Do not run it unchanged.
  Use a separately chosen local generator and record its outputs; local hardware
  requirements must be checked before selecting that model. Keep CI replay-only.
- Change a retrieval setting or prompt, record the candidate, and run the same
  evaluator. Keep controlled failure-injection fixtures separately labelled.
- Check dataset/model licensing and attribution before downloading or redistributing
  artifacts. No downloads or model calls were performed in this task.

## Limits

Scientific answer correctness needs more than required-phrase matching. Annotate
appropriate checks and report their limits; do not present keyword coverage as
medical validity. A general semantic answer evaluator remains separate future work.
The tutorial does not supply a ready-made baseline compatible with our contracts.

Sources reviewed: [Haystack RAG tutorial](https://haystack.deepset.ai/tutorials/35_evaluating_rag_pipelines),
[BEIR paper](https://arxiv.org/abs/2104.08663).
