# Selected integration example: Haystack + PubMedQA

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
