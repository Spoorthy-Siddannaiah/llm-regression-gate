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
