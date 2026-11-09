# v0.1.0 publication handoff

The regression-catching MVP is ready for repository review. The README and
[five-case demo](demo.md) are the entry points. The clinical dataset extension is
future work, not required to demonstrate this release's implemented scope.

## Release contents

- Typed evaluator, versioned policies, reports, CLI, and opt-in local generation.
- Handwritten pass/fail fixtures, clearly labelled separately from actual outputs.
- Three actual SQuAD recordings: observed baseline, degraded top-one candidate,
  and constrained-citation candidate. All include raw evidence for offline replay.
- Tests and eight CI replay checks, including both real rejection and real pass.
- Attribution for the SQuAD adaptation; original code remains unlicensed by choice.

Generated reports, local workflow output, model files, virtual environments, and
local environment files are excluded from publication. Raw versioned model evidence
under `recordings/` is intentionally included. Targeted credential-pattern scans
are useful checks, not a guarantee that a repository contains no sensitive material.

## Proposed GitHub repository

- Owner: `Spoorthy-Siddannaiah` (authenticated GitHub CLI account).
- Name: `llm-regression-gate`.
- Description: “Reproducible RAG regression gates with fixed baselines, local model evidence, and CI replay.”
- Proposed visibility: public for portfolio review; publication needs explicit confirmation.

No remote is configured and nothing has been pushed. The working agreement still
says “do not push or publish”; prepare locally first, then confirm this exact
destination and visibility with the owner.

After authorized publication, inspect the first hosted `Regression checks` run
and downloadable reports. Only then claim hosted CI is verified. Configure the
`Tests and recorded-response gate` check as required if the account/repository's
branch rules support it. Passing CI is not deployment or clinical release approval.

## Interview walkthrough

Explain the fixed dataset and baseline, show the top-one regression being rejected,
then show the citation-schema fix passing without weaker thresholds. Distinguish
limited phrase/ID checks from semantic correctness. Finish with the missing pieces:
fresh inference for each PR, representative domain labels, and production operation.

## Audit-fix working tree

The owner has explicitly prohibited commits, remote configuration and publication
for this implementation task. Review the uncommitted audit changes and
[audit-fix verification](audit-fixes.md) first. Public release remains a separately
authorized action, followed by hosted Actions verification. Code stays unlicensed.
