import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def command(output, references=None):
    return [
        sys.executable, str(ROOT / "scripts/evaluate_answer_alternatives.py"),
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"),
        "--references", str(references or ROOT / "datasets/squad/v1/references.json"),
        "--baseline", str(ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json"),
        "--candidate", str(ROOT / "recordings/squad/llama3.2-bm25-top1-v1/recording.json"),
        "--output", str(output),
    ]


def test_real_diagnostic_reproduces_measurement_and_refuses_overwrite(tmp_path):
    output = tmp_path / "diagnostic.json"
    run = subprocess.run(command(output), cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(output.read_text()) == json.loads(
        (ROOT / "benchmarks/squad-alternatives-v1.json").read_text()
    )
    before = output.read_bytes()
    assert subprocess.run(command(output), capture_output=True).returncode == 2
    assert output.read_bytes() == before


@pytest.mark.parametrize("problem", ["missing_case", "source_mismatch", "wrong_span"])
def test_bad_reference_annotations_fail_before_output(tmp_path, problem):
    references = json.loads((ROOT / "datasets/squad/v1/references.json").read_text())
    first = next(iter(references))
    if problem == "missing_case":
        references.pop(first)
    elif problem == "source_mismatch":
        references[first]["source_id"] = "unknown-source"
    else:
        references[first]["answers"][0]["answer_start"] = 0
    path = tmp_path / "references.json"
    path.write_text(json.dumps(references))
    output = tmp_path / "output.json"
    run = subprocess.run(command(output, path), capture_output=True, text=True)
    assert run.returncode == 2
    assert "ERROR" in run.stderr
    assert not output.exists()
