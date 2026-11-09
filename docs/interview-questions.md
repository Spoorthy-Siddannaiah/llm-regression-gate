# Interview practice

## Typed evaluation contracts

Why should a missing candidate case stop the comparison instead of being silently
excluded from its score?

## Validated file loading

Why should an unknown citation be accepted for scoring, while a missing response
case prevents the comparison?

Consider the distinction between invalid evaluation inputs and poor application
behaviour, and how silently dropping cases could distort a comparison.

## Deterministic required-fact checks

An answer says: "The limit is not 30 days. No proof of purchase is required."
It passes our required-phrase checks. Why does this happen, and what additional
evidence would you need before treating it as a correct answer?

## Citation IDs and retrieval Recall@K

A candidate retrieves every relevant document and cites the expected source, but
its answer gives the wrong refund window. Why can Recall@K and citation-ID checks
still look good? Which separate check would expose this fixture's failure?

## Evaluation runner

Why must baseline and candidate use the same evaluator version and retrieval K,
even though their model, prompt, or retrieval configurations may differ?

## Regression gate

Why do we need both a baseline-relative regression limit and an absolute candidate
quality requirement? What happens if baseline and candidate both fail the same
critical case, or if improvements elsewhere hide that failure in the average?

## Reports and baseline acceptance

Why should a regression report preserve the baseline identity, evaluator settings,
and gate policy? If a baseline has known failures, can a passing comparison alone
establish that the candidate is acceptable for release?

## CLI and CI integration

Why should a missing recording file or report-write failure return an execution
error rather than a quality-regression exit code? Should either outcome allow
a deployment, and how would the team's response differ?

## GitHub Actions regression checks

Why must the intentionally degraded fixture return exactly exit 1, rather than
just any nonzero exit? What would go wrong if CI used `continue-on-error` for the
real candidate gate?

## Dataset provenance

Why is a reference answer not the same as a pipeline baseline? How could using
reference answers or per-question relevant documents during candidate generation
make a RAG evaluation misleading?

## Real SQuAD integration

Why must alternative human answers be treated differently from several required
facts? What misleading failures could result if a correct answer uses a different
annotated span than our currently selected first span?

## Local BM25 retrieval

Our real-data Recall@1 is 0.68 and Recall@5 is 0.88. Why might increasing K help
retrieval but still hurt end-to-end answer quality or latency? Why must relevance
labels be kept out of the retriever's inputs?

## Local model baseline recording

Why must we capture the model digest, prompt, generation settings, and corpus hash
alongside a recording? Does temperature zero make baseline regeneration perfectly
deterministic, and does a completed run mean the baseline is release-ready?

## Real candidate experiment

We reduced retrieval output from three passages to one and evaluated both at
Recall@3. Why is the resulting coverage drop not evidence that BM25 ranking got
worse? Why use a relative-only policy to demonstrate regression separately from
absolute quality requirements the baseline already misses?

## Real recordings in CI

Why is CI green when its expected-rejection step observes a real candidate's exit 1?
How does that differ from a production candidate gate that must return exit 0,
and why does replaying committed recordings not evaluate new prompt code by itself?

Simple answer: this is a test of the detector. It expects the known bad candidate
to return exit 1; getting that expected rejection makes the test pass. A new
production candidate instead needs exit 0 from its quality gate. Replaying saved
answers does not run a changed prompt or produce fresh model responses.

## Manifest integrity

The dataset version label is unchanged, but the corpus bytes differ from the
recording manifest. Should the CLI report a quality regression or an input error,
and why must it stop before scoring?

## Alternative answers

Why should "Norseman OR Viking" be represented differently from "30 days AND proof
of purchase"? Why would automatically adding a model's answer as a new accepted
alias undermine regression testing?

## Optional diagnostics in reports

Why should enabling a new diagnostic leave the existing release gate unchanged
until its behaviour has been reviewed? How would you distinguish "reported for
inspection" from "enforced as a release requirement" in the API and report?

## Citation existence versus support

Why can a cited source exist in the corpus and still be an invalid citation for
the answer? Why should an ID absent from the corpus be labelled unknown rather
than automatically claimed to be deliberately fabricated?

## Unknown-citation gate policy

Baseline and candidate each contain one unknown citation. Why might an absolute
limit reject the candidate while the regression limit passes? Why does having
zero unknown IDs still fail to prove that citations support the answer?

## V2 replay checks in CI

Why should an expected-rejection test verify the failure code and evidence, rather
than accepting any exit 1? How could it otherwise stay green while testing the
wrong policy behaviour?

## Architecture and demo defence

A reviewer asks whether a green CI run proves the changed RAG prompt is safe.
Which parts of this demo are actually verified, and what additional generation
step would be needed before making that claim?

## Code provenance

Why is a Git commit insufficient to reproduce a run from a dirty working tree?
Why should replay validate an old baseline's saved metadata without requiring its
source hashes to match the current checkout?

## Candidate freshness

Why should candidate freshness check the expected revision and source hashes while
allowing the baseline to reference older code? Why is comparing a candidate to its
own saved snapshot insufficient to prove that it came from a new PR?

## Local generation orchestration

Why should a generation failure stop comparison and return exit 2, while a complete
candidate that fails quality returns exit 1? Which artifacts would you inspect
before accepting a run as completed?

## Actual local workflow result

The candidate matches the baseline's aggregate scores and unknown-citation count,
but the gate returns exit 1. Why can this be correct? Explain the difference between
an absolute quality requirement, a regression, and an execution error.

## Constrained citation generation

Why constrain citation choices to retrieved IDs during generation while preserving
unknown IDs in the recording parser? Can a valid source ID still support a wrong
answer, and how would you evaluate that separately?
