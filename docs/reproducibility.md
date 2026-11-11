# Reproducibility and package identity

Use a source checkout for demonstrations: datasets and recordings are deliberately
separate from the installable evaluator wheel. Nothing downloads a model or calls
a paid provider during the commands below. Initial Python/package installation can
require internet; the installed tests and replay run without model inference.

## Names and verified versions

| Surface | Name |
| --- | --- |
| Project / repository | LLM Regression Gate / `llm-regression-gate` |
| Python distribution | `llm-reliability-platform` |
| Import package | `llm_reliability` |
| Installed command | `llm-reliability` |

These existing names are retained for compatibility. The verified runtime is
Python 3.12.13, with uv 0.13.7 in CI. Project metadata supports Python 3.12+;
other versions are not claimed as tested. Pydantic and pytest versions come from
`uv.lock`. Build dependencies are pinned in `pyproject.toml`.

## Fresh environment and offline demonstration

From a fresh checkout, using an installed uv:

```sh
uv sync --python 3.12.13 --locked
uv run --locked pytest -q
uv run --locked python scripts/demo.py
uv run --locked python scripts/verify_replays.py --output-dir reports/review-new
```

Existing report directories are refused. The demo defaults to a new temporary
location, so repeated invocations need no cleanup. The two verification wrappers
exit 0 when all known decisions match, including intentional quality failures.
The underlying comparison CLI uses 0 = pass, 1 = gate failure, 2 = execution error.

To verify the current working source with an independently installed environment:

```sh
uv run --locked python scripts/verify_snapshot.py --output-dir /tmp/llm-source-review-new
```

Choose a new path. This copies tracked and nonignored proposed files plus existing
Git metadata, installs locked dependencies, runs the full tests and eight replays.
It is an isolated **source snapshot**, not a fresh Git clone or a hosted CI run.
It copies Git metadata because tests inspect provenance; it does not change refs,
create commits, configure remotes or push.

## Build and test the installed wheel

Use new output/environment paths. These commands do not change the dependency lock:

```sh
uv build --python 3.12.13 --out-dir /tmp/llm-review-dist-new
uv export --locked --no-dev --no-emit-project --no-hashes --format requirements-txt --output-file /tmp/llm-runtime-new.txt
uv venv --python 3.12.13 /tmp/llm-wheel-review-new
uv pip install --python /tmp/llm-wheel-review-new/bin/python -r /tmp/llm-runtime-new.txt /tmp/llm-review-dist-new/llm_reliability_platform-0.1.0-py3-none-any.whl
/tmp/llm-wheel-review-new/bin/llm-reliability --help
```

For a comparison, use that installed command with absolute paths to this checkout's
data, recordings and configuration, as in the [direct demo](demo.md). Run from a
directory outside the checkout to check that the installed package is being used.
The wheel intentionally contains no datasets, model weights or recording evidence.

Replaying fixed outputs is reproducible. Regenerating model outputs, even at
temperature zero with a seed, is not guaranteed to reproduce identical responses.
The [pinned SQuAD importer](../datasets/squad/v1/README.md) separately documents how
to reconstruct the dataset bytes from the upstream source.
