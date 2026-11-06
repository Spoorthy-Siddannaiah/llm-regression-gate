import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_measurement_script_reproduces_recorded_real_results_and_refuses_overwrite(tmp_path):
    output = tmp_path / "measurement.json"
    command = [
        sys.executable, str(ROOT / "scripts/evaluate_retrieval.py"),
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"), "--output", str(output),
    ]
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads(output.read_text())
    committed = json.loads((ROOT / "benchmarks/squad-bm25-v1.json").read_text())
    assert report["mean_recall"] == committed["mean_recall"]
    assert report["settings"] == committed["settings"]
    assert report["case_count"] == 25
    assert report["input_sha256"]["sources"] == hashlib.sha256(
        (ROOT / "datasets/squad/v1/sources.json").read_bytes()
    ).hexdigest()
    # Freeze source ranking, not platform-specific floating-point score bytes.
    for actual, expected in zip(report["cases"], committed["cases"], strict=True):
        assert actual["case_id"] == expected["case_id"]
        assert [hit["source_id"] for hit in actual["ranked_hits"]] == [
            hit["source_id"] for hit in expected["ranked_hits"]
        ]
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode == 2
    assert output.read_bytes() == before
