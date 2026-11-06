import json
from pathlib import Path
import subprocess
import sys

import pytest

from llm_reliability.cli import main


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets/support_policy/v1/dataset.json"
BASELINE = ROOT / "recordings/baseline.synthetic.v1.json"
CANDIDATE = ROOT / "recordings/candidate.synthetic.v2.json"
ACCEPTED_CANDIDATE = ROOT / "recordings/candidate.synthetic.v1.json"


def arguments(output, candidate=CANDIDATE):
    return ["--dataset", str(DATASET), "--baseline", str(BASELINE),
            "--candidate", str(candidate), "--output-dir", str(output)]


@pytest.mark.parametrize("module", ["llm_reliability", "llm_reliability.cli"])
@pytest.mark.parametrize("candidate, expected", [
    (BASELINE, 0), (ACCEPTED_CANDIDATE, 0), (CANDIDATE, 1),
])
def test_process_exit_codes_and_reports(tmp_path, module, candidate, expected):
    output = tmp_path / "reports"
    before = BASELINE.read_bytes()
    process = subprocess.run(
        [sys.executable, "-m", module, *arguments(output, candidate)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert process.returncode == expected, process.stderr
    assert process.stderr == ""
    assert ("PASS" if expected == 0 else "FAIL") in process.stdout
    assert json.loads((output / "report.json").read_text())["passed"] == (expected == 0)
    assert (output / "report.md").exists()
    assert BASELINE.read_bytes() == before


def test_missing_file_returns_execution_error_without_reports(tmp_path, capsys):
    output = tmp_path / "reports"
    missing = tmp_path / "missing.json"
    assert main(arguments(output, missing)) == 2
    assert str(missing) in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("flag", ["--policy", "--settings"])
@pytest.mark.parametrize("content", ['{"broken":', '{"unexpected": true}'])
def test_invalid_config_identifies_file(tmp_path, capsys, flag, content):
    config = tmp_path / "invalid.json"
    config.write_text(content)
    output = tmp_path / "reports"
    assert main([*arguments(output), flag, str(config)]) == 2
    assert str(config) in capsys.readouterr().err
    assert not output.exists()


def test_explicit_configs_are_preserved_in_report(tmp_path):
    output = tmp_path / "reports"
    assert main([
        *arguments(output), "--policy", str(ROOT / "configs/gate.synthetic.v1.json"),
        "--settings", str(ROOT / "configs/evaluator.v1.json"),
    ]) == 1
    data = json.loads((output / "report.json").read_text())
    assert data["policy"]["fact_coverage"]["minimum"] == 0.9
    assert data["evaluation"]["settings"]["retrieval_k"] == 3


def test_report_error_takes_precedence_over_gate_failure(tmp_path, capsys):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "report.json"
    sentinel.write_text("preserve")
    assert main(arguments(output)) == 2
    assert "ERROR" in capsys.readouterr().err
    assert sentinel.read_text() == "preserve"


def test_unexpected_failure_is_not_reported_as_regression(tmp_path, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError("private response payload")

    monkeypatch.setattr("llm_reliability.cli.compare_and_gate", fail)
    assert main(arguments(tmp_path / "reports")) == 2
    error = capsys.readouterr().err
    assert "RuntimeError" in error
    assert "private response payload" not in error


@pytest.mark.parametrize("args, expected", [([], 2), (["--help"], 0)])
def test_argument_errors_and_help(args, expected):
    with pytest.raises(SystemExit) as caught:
        main(args)
    assert caught.value.code == expected
