# Audit fixes and reproducible verification

**Historical audit record:** the task below predates publication. Its original
commit/working-tree observations describe that audit snapshot, not current Git
state. For current status, see [publication](publication.md); for commands and
package identity, see [reproducibility](reproducibility.md).

The audit-fix task started at clean HEAD
`2ad69ec05ef5697d88befe3be8bb84994f7801ae`. At that stage, changes were intentionally uncommitted:
the owner prohibited commits, remotes, publication, model calls and license changes.
All historical datasets, recordings, benchmark artifacts and policy thresholds remain
unchanged. Original code remains unlicensed.

## Implemented changes

1. The recorder hashes captured dataset/corpus bytes and parses those exact bytes.
   Original files are rechecked before completion; drift preserves partial evidence
   without a completed manifest. Restricted raw evidence is not an error log.
2. Provider failures expose stage, fixed error categories, validation codes and
   sanitized locations. No provider exception representation or raw body enters
   stdout/stderr. Fictional-marker tests cover malformed JSON, extra fields,
   duplicate citations, invalid stop reasons, transport and unexpected exceptions.
3. Recording-origin descriptions are neutral for real and synthetic inputs.
4. JSON parsing rejects duplicate object keys (including nested keys) without
   echoing the key. Nonstandard numeric constants are rejected. Required source
   labels must exist when a corpus is supplied/available; unknown observations
   are still retained for scoring.
5. Schema-4 reports show paired metric deltas, case status, and critical highlights.
   `max_regressed_cases` is optional, nonnegative and disabled when omitted. Cases
   with any metric drop count once; gains do not cancel a loss within that case.
   No slice constraints or semantic judge were added.
6. CLI receipts contain input hashes, evaluator package-source hashes, evaluator
   and policy versions, and `matched`/`not_requested` target status. Optional policy,
   settings, reference and target file hashes are included when supplied. No raw
   answers or passages enter receipts. Input/source drift prevents report writing.
   Direct API renderers show null provenance unless a receipt is explicitly supplied.

Report schemas 1–3 remain historical artifacts. New reports use **schema 4**, an
intentional output migration; policy versions, metric meanings, and unconfigured
policy decisions remain unchanged. Existing benchmark comparisons are checked
against the unchanged decision payload after removing new report metadata.
See the [actual report excerpt](example-regression.md).

## Verified action and build pins

Verified via official GitHub release endpoints and peeled tag refs on 2026-11-09:

| Action | Official release | Full SHA |
| --- | --- | --- |
| checkout | [v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| upload-artifact | [v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| setup-uv | [v10.3.3](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3) | `68559e99cc807c1eb7e9238fd43a15bba460eec2` |

The workflow selects supported `ubuntu-24.04`; the image still receives updates.
Read-only contents permission and `persist-credentials: false` are retained.
Python 3.12.13 and uv 0.13.7 are explicit. The first hosted run showed that the
previous uv 0.7.12 pin lacked this Python version's Linux download; the updated
pin recognizes the required Linux x86_64 build. Eight offline scenarios are retained;
no fresh inference, deployment or hosted verification is claimed.

`pyproject.toml` pins Hatchling 1.27.0 and its Python-3.12+ build dependency closure:
packaging 26.3, pathspec 1.1.1, pluggy 1.7.0, trove-classifiers 2026.9.21.13.
Versions and requirements were checked against PyPI metadata; no runtime packages
were upgraded. The standard build requirements apply to PEP 517 installation,
not just uv-specific configuration. The existing runtime/test lock remains unchanged.

## Commands

From the repository root (use new output directories):

```sh
uv sync --python 3.12.13 --locked
uv run --python 3.12.13 --locked pytest -q -p no:cacheprovider
uv run --python 3.12.13 --locked pytest -q tests/test_audit_recording.py tests/test_audit_inputs_cases.py tests/test_evaluation_receipt.py
uv run --python 3.12.13 --locked python scripts/verify_replays.py --output-dir reports/audit-replays-new
uv build --python 3.12.13 --out-dir /tmp/llm-audit-dist-new
uv run --python 3.12.13 --locked python scripts/verify_snapshot.py --output-dir /tmp/llm-audit-snapshot-new
```

`verify_replays.py` checks all eight expected exits/reasons, schema-4 evidence,
16 report files, and all 54 baseline hashes against the existing benchmark snapshot.
Its own exit 0 means the known scenarios behaved as expected, including rejections.

`verify_snapshot.py` copies tracked and nonignored proposed files, excluding local
runs/reports/environments, into a fresh directory. Existing `.git` metadata is copied
only so provenance tests can inspect the original revision; no history or remote
is created/changed. It performs a fresh locked install, tests and eight replays.
Because commits are prohibited, this is an isolated uncommitted release-source
snapshot, not a claim of a newly committed clean checkout or hosted verification.

Build outputs, reports and isolated environments stay outside publication. Review
raw evidence separately before adding any future recording. Never introduce real
patient data into this repository. Git-ignore rules are not data-loss prevention.

## Remaining limits

Phrase assertions do not handle negation, contradiction or paraphrases. Citation
membership is neither relevance nor claim support. The selected 25-question slice
is not representative and contains no reviewed clinical criticality labels or
explicit correct-abstention cases. No judge, PHI detection, latency/cost gate,
trusted production traces, production deployment or healthcare compliance exists.
Before/after file checks are not transactions against hostile concurrent writers.
Receipts and manifests are integrity evidence, not signed execution attestation.
Hosted execution was subsequently verified after owner-authorized publication;
see [the revision-specific record](publication.md). This does not verify local edits.

## Original audit verification results

- **356 tests passed** locally and after a fresh locked installation of an isolated
  current-source snapshot. No tests were reported skipped.
- All eight replay scenarios passed expected outcomes: **0/1/0/1/0/1/1/0**.
  The eight actual workflow shell bodies were separately parsed, syntax-checked
  and executed using installed virtual-environment launchers, with all 16 reports.
- Five demo evaluations returned **0/1/1/2/0** as documented.
- Source distribution and wheel built successfully. The wheel was installed into
  a separate temporary environment using runtime versions exported from uv.lock;
  its console entry point passed the real citation-enum comparison from /tmp.
- Local documentation targets, whitespace and package archive exclusions passed.
- All 54 baseline files match their original commit `23bb9fa`; all original
  datasets, recordings, benchmarks, policy files and uv.lock remain unchanged.
- Targeted credential-pattern scans covered proposed files and 407 reachable
  historical blobs, with no matches. No dedicated secret scanner or comprehensive
  security certification is claimed.
- HEAD remains `2ad69ec`; index is unchanged; no remote, license, commit or push.
  Changes remain uncommitted for owner review. **Hosted CI is still unverified.**

Additional wheel smoke-test commands (use fresh paths):

```sh
uv export --locked --no-dev --no-emit-project --no-hashes --format requirements-txt --output-file /tmp/llm-runtime-new.txt
uv venv --python 3.12.13 /tmp/llm-wheel-env-new
uv pip install --python /tmp/llm-wheel-env-new/bin/python -r /tmp/llm-runtime-new.txt /tmp/llm-audit-dist-new/llm_reliability_platform-0.1.0-py3-none-any.whl
/tmp/llm-wheel-env-new/bin/llm-reliability --help
```

The actual smoke test additionally executed the citation-enum replay with absolute
input paths from /tmp; see [the saved candidate's replay arguments](../recordings/squad/llama3.2-bm25-citation-enum-v2/README.md),
substituting this installed console command and a new report directory.
