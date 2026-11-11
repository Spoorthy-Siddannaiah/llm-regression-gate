"""The interviewer demo must show real report evidence and fail on execution errors."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/demo.py"


def test_demo_runs_from_another_directory_and_displays_verified_reports(tmp_path):
    output = tmp_path / "reports"
    process = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(output)],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
    )
    assert process.returncode == 0, process.stderr
    assert process.stderr == ""
    assert "84.0% -> 68.0% (-16.0 percentage points)" in process.stdout
    assert "80.0% -> 68.0% (-12.0 percentage points)" in process.stdout
    assert "Baseline answer: 'Von Miller'; candidate answer: ''" in process.stdout
    assert "Unknown citation occurrences: 1 -> 0" in process.stdout
    assert "DEMO VERIFIED" in process.stdout
    assert "no fresh model inference" in process.stdout
    assert len(list(output.glob("*/report.json"))) == 8
    assert len(list(output.glob("*/report.md"))) == 8
    assert json.loads((output / "squad-regression/report.json").read_text())["passed"] is False
    assert json.loads((output / "citation-enum/report.json").read_text())["passed"] is True


def test_demo_refuses_existing_output_without_reporting_success(tmp_path):
    marker = tmp_path / "report.json"
    marker.write_text("preserve existing work")
    process = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(tmp_path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
    )
    assert process.returncode == 2
    assert "demo not verified" in process.stderr
    assert "DEMO VERIFIED" not in process.stdout
    assert marker.read_text() == "preserve existing work"


def test_demo_does_not_claim_success_when_verifier_returns_no_reports(tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("portfolio_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "", ""))
    assert module.main(["--output-dir", str(tmp_path / "missing")]) == 2
    captured = capsys.readouterr()
    assert "DEMO VERIFIED" not in captured.out
    assert "demo did not complete" in captured.err
