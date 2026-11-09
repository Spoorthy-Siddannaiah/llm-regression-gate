# Dataset recommendation for the voize application

Reviewed 2026-11-09. Recommendation only: no dataset imported or evaluation changed.

## Role fit

The [Senior ML Engineer – NLP posting](https://jobs.ashbyhq.com/voize/f4939c9a-041c-4383-80e0-1072c8f48241)
emphasizes care documentation agents, benchmarks, regression tests, failure
investigation, and quality/speed/privacy trade-offs. Python evaluation tooling and
structured outputs are directly relevant. The employer's public
[job-board API](https://api.ashbyhq.com/posting-api/job-board/voize) supplied the
description because the linked page requires JavaScript.

Our existing error → controlled change → fixed-baseline comparison workflow fits
that engineering work. SQuAD shows the mechanics, but documentation data would
make the application story more relevant. This portfolio does not demonstrate
production clinical deployment or model training experience yet.

## Recommended next dataset: ACI-Bench

[ACI-Bench's paper](https://www.nature.com/articles/s41597-023-02487-3) describes
207 simulated clinical dialogue/reference-note pairs, with validation and held-out
test splits. It evaluates conversation-to-note generation, close to the role's
documentation task. It is English and simulated, not German nursing records or
voize production traces. The paper discusses its limited representativeness.

The [publisher's data repository](https://github.com/microsoft/clinical_visit_note_summarization_corpus)
provides downloadable data under
[CC BY 4.0](https://github.com/microsoft/clinical_visit_note_summarization_corpus/blob/main/LICENSE).
Keep author attribution, license and modification notices when importing a slice.
The repository is archived/read-only; pin a revision and file hashes rather than
depending on updates. Publicly released does not mean real-patient production data.

Why this choice: it supports a concrete documentation demo using public inputs and
reference notes, with an explicit reuse license. We can inspect a small subset
locally before committing to longer inference runs.

An alternative is [MTS-Dialog](https://github.com/abachaa/MTS-Dialog), which offers
shorter dialogue/note-section pairs. It may fit the current small model's context
and output budget better, but full documentation is better represented by ACI-Bench.

## Proposed separate benchmark, not a drop-in SQuAD replacement

1. Pin the upstream revision, license, hashes, split and stable encounter IDs.
   Inspect a small validation slice first; reserve test encounters from tuning.
2. Keep dialogue input separate from reference notes and human-reviewed assertions.
   Reference notes must never enter the model prompt as evidence for their own output.
3. Start with short, explicitly scoped extraction tasks from dialogue, rather than
   pretending the current 256-token output budget supports complete clinical notes.
   This would be a derived extraction benchmark, not official ACI-Bench scoring.
4. Annotate source spans and expected fields. Later add checks for omissions,
   negation, invented facts and incorrect medication attributes. Literal phrase
   matching alone cannot establish clinical correctness; these checks are not implemented.
5. Record an observed baseline, then introduce a known controlled defect and run
   the same gate. Never equate a reference note with our model baseline recording.

This task is primarily grounded extraction/summarization, not automatically RAG.
Do not mix patient encounters in one retrieval pool. If retrieval is added, confine
it to the current encounter and explicitly annotate relevant spans before applying
Recall@K. Full-note generation needs a separate prompt, output budget and evaluator;
the current QA generator is not a validated clinical documentation system.

An honest application description after implementation would be: “Built a local
regression evaluation workflow for simulated clinical documentation, with versioned
inputs, fixed baselines, evidence reports, and controlled failure experiments.”
Today, describe the implemented QA workflow and this planned domain extension separately.
