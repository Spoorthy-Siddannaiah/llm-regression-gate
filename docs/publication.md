# Publication status and review checklist

The project is public at
[Spoorthy-Siddannaiah/llm-regression-gate](https://github.com/Spoorthy-Siddannaiah/llm-regression-gate).
The default branch is `main`. Publication is repository hosting, not application
deployment, production acceptance or clinical release approval.

## Verified published state

The [hosted run on `fd89a8c`](https://github.com/Spoorthy-Siddannaiah/llm-regression-gate/actions/runs/42788109117)
passed tests, all eight expected replay outcomes and report upload. A prior run on
`995ef72` also had all 16 report files downloaded and checked. These observations
apply to those revisions, not to subsequent local changes. Branch-protection
requirements have not been verified.

## Review entry points

- [README](../README.md): problem, measured experiment, architecture and limitations.
- [Terminal demo](demo.md): actual report evidence without a model server.
- [Reproducibility](reproducibility.md): locked environment and installed-wheel checks.
- [Portfolio audit](portfolio-audit.md): findings and the current polish scope.

## Before any additional publication

1. Inspect the full diff; preserve datasets, baseline hashes, recordings and policies.
2. Run tests, eight replays, package builds and relevant environment checks.
3. Review raw evidence for private data before adding future recordings. Ignored
   local reports, run directories, caches, environments and model files stay local.
4. Keep original code unlicensed unless the owner explicitly changes that choice;
   preserve SQuAD's separate CC BY-SA attribution and notices.
5. Obtain explicit owner approval before committing or pushing the current polish.
6. Push only the intended branch, then inspect the hosted run for that exact revision.
   Retain internal refs, private backups and original email metadata outside publication.

A successful replay verifies that known examples behaved as expected. It does not
establish semantic correctness, fresh PR inference or deployment eligibility.
