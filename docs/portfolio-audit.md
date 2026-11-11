# AI engineering portfolio audit

Audit date: 2026-11-11. Starting revision: `fd89a8c`. The working tree and index
were clean. All 265 tracked files were read for text/JSON/Python validity; source
modules, package metadata, test coverage, recordings, workflow and current-facing
docs were reviewed. This is an engineering review, not a security certification.
The initial locked installation and full test baseline passed: **356 tests**.

## Critical

No blocking evaluation defect was identified in this review. Release checks must
still establish the following before proposed changes are considered verified:

- Preserve evaluator source, policies, datasets, recordings, benchmarks and uv.lock.
- Preserve all 54 fixed-baseline hashes and expected gate outcomes.
- Keep a distinction between quality rejection (1) and execution failure (2).
- Avoid claims of semantic correctness, clinical validity or fresh inference per PR.
- Leave changes uncommitted and unpushed pending owner approval.

## Recommended

| Finding | Consequence | Proposed improvement |
| --- | --- | --- |
| README mixed the review narrative with hundreds of reference lines | A reviewer must work to identify the actual contribution | Short overview with experiment, reproduction, architecture and limitations; move contracts to linked reference |
| Existing replay verifier printed scenario exits but little explanatory evidence | Hard to demonstrate the engineering result quickly | New terminal wrapper displays generated report metrics and saved answer evidence, reusing all existing verification |
| Some current-facing docs still said unpublished or hosted CI unverified | Contradicts public repository and successful hosted runs | Current publication guide; clearly label historical audit observations |
| Repository, distribution, import and executable names differ | Installation can look inconsistent | Document identities, retain compatible names, add package README and repository metadata |
| Two v1 CI negative steps checked exit 1 without inspecting reports | A different quality failure might satisfy those particular steps | Assert exact failure-code sets and relevant metric/case evidence; retain all thresholds |
| Readme did not distinguish wheel contents from source-checkout assets | Installed users might expect included datasets or demos | Explicit wheel/source distinction and installed-wheel smoke instructions |

## Optional follow-ups, intentionally deferred

- Introduce a formatter/linter and gradual static type checking as a separate change.
  Core contracts are typed, but scripts, some dictionaries and serializer methods
  are not fully annotated; no lint/type-check pass is claimed.
- Split longer orchestration/reporting functions if future feature work justifies
  it. Existing tests and narrow modules are a stronger reason to preserve working
  code than to refactor for appearance.
- Reduce duplicated workflow/replay scenario declarations through a reviewed
  shared contract; this pass strengthens existing workflow assertions instead.
- Broaden reviewed labels, calibrate semantic evaluators, add fresh PR generation,
  repeated-run measurements and appropriate domain evidence. These require new
  experiments, not README wording.
- Check repository branch protection separately. CI success does not prove that
  merging is blocked, deploy anything, or certify model quality.

## Evidence and design assessment

- Typed validation enforces exact case coverage, duplicate rejection and compatible
  dataset identity/version. Missing inputs fail explicitly.
- Scoring, acceptance policies, report writing and optional generation are separate.
  Baseline/candidate use the same evaluator settings; no baseline promotion occurs.
- Phrase coverage is literal; citation labels and membership are distinct. Scores
  are not SQuAD EM/F1, claim-support evaluation or a semantic accuracy measure.
- Recorded requests preserve actual retrieved contexts; tests compare observations
  with raw responses and verify the controlled retrieval/schema differences.
- The baseline is an observational reference with known defects. Zero floors can
  allow unchanged poor quality, and aggregate metrics can mask individual losses
  unless the optional case-count limit is selected. These limits remain documented.
- SHA-256 manifests and receipts support byte integrity, not trusted execution.
  Report writes remain non-atomic. Dataset scale and privacy limits are explicit.
- The wheel intentionally packages the evaluator. Demonstration data and recordings
  remain in the checkout; the project is not an installed standalone dataset bundle.

## Verification record

The proposed working tree passed 359 tests locally and in an isolated source
snapshot, eight original replays, and all eight actual CI replay shell bodies
with their report assertions. Wheel/sdist builds and an installed-wheel real
comparison outside the source checkout passed. All 207 protected existing files
(including uv.lock) and all 54 baseline hashes match the initial snapshot.
Details are recorded in [progress](progress.md).
Use [reproducibility](reproducibility.md) for the exact commands. Existing hosted
success applies to the published revision only; no new hosted run is claimed for
this uncommitted polish. No software license or paid API dependency is added.
