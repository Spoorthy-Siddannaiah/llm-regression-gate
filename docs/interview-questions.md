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
