import json
from pathlib import Path
import subprocess
import sys

import pytest

from llm_reliability.alternative_diagnostics import build_diagnostic
from llm_reliability.gates import compare_and_gate
from llm_reliability.loading import load_comparison
from llm_reliability.reports import render_json, render_markdown, write_reports


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets/squad/v1/dataset.json"
SOURCES = ROOT / "datasets/squad/v1/sources.json"
REFERENCES = ROOT / "datasets/squad/v1/references.json"
BASELINE = ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json"
CANDIDATE = ROOT / "recordings/squad/llama3.2-bm25-top1-v1/recording.json"


@pytest.fixture
def evidence():
    return (
        compare_and_gate(load_comparison(DATASET, BASELINE, CANDIDATE)),
        build_diagnostic(DATASET, SOURCES, REFERENCES, BASELINE, CANDIDATE),
    )


def test_extended_reports_show_evidence_without_changing_gate(evidence, tmp_path):
    gate, diagnostic = evidence
    before = gate.model_dump_json(), diagnostic.model_dump_json()
    payload = json.loads(render_json(gate, answer_alternatives=diagnostic))
    assert payload.pop("report_schema_version") == 2
    assert payload.pop("diagnostics")["answer_alternatives"] == diagnostic.model_dump(mode="json")
    assert payload == gate.model_dump(mode="json")
    text = render_markdown(gate, answer_alternatives=diagnostic)
    assert "**Gate: FAIL**" in text
    assert "Report schema: 2" in text
    assert "diagnostic only" in text
    assert "| baseline | 0.840000 | 0.840000 |" in text
    assert "| candidate | 0.680000 | 0.680000 |" in text
    assert "Allowed alternatives | Matched | Unmatched" in text
    assert diagnostic.input_sha256["references"] in text
    paths = write_reports(gate, tmp_path / "extended", answer_alternatives=diagnostic)
    assert json.loads(paths[0].read_text())["report_schema_version"] == 2
    assert paths[1].read_text() == text
    assert before == (gate.model_dump_json(), diagnostic.model_dump_json())


def test_disabled_diagnostic_preserves_default_output(evidence):
    gate, _ = evidence
    assert render_json(gate) == render_json(gate, answer_alternatives=None)
    assert render_markdown(gate) == render_markdown(gate, answer_alternatives=None)
    payload = json.loads(render_json(gate))
    assert payload["report_schema_version"] == 1
    assert "diagnostics" not in payload
    assert "Optional answer alternatives" not in render_markdown(gate)


def test_mismatched_diagnostic_rejected_before_writing(evidence, tmp_path):
    gate, diagnostic = evidence
    diagnostic.results.candidate.recording_id = "different-recording"
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="candidate.*does not match"):
        write_reports(gate, output, answer_alternatives=diagnostic)
    assert not output.exists()


def test_optional_evidence_is_escaped_in_markdown(evidence):
    gate, diagnostic = evidence
    case = diagnostic.results.baseline.cases[0]
    case.alternatives = ["<script>|[bad](url)"]
    case.alternative_result.matched_alternatives = ("<script>|[bad](url)",)
    text = render_markdown(gate, answer_alternatives=diagnostic)
    assert "<script>" not in text
    assert r"&lt;script&gt;\|\[bad\]\(url\)" in text


def command(output, candidate):
    return [
        sys.executable, "-m", "llm_reliability", "--dataset", str(DATASET),
        "--sources", str(SOURCES), "--require-manifests", "--baseline", str(BASELINE),
        "--candidate", str(candidate), "--output-dir", str(output),
    ]


@pytest.mark.parametrize("candidate, expected", [(BASELINE, 0), (CANDIDATE, 1)])
def test_cli_opt_in_preserves_exit_code_and_gate_payload(tmp_path, candidate, expected):
    plain = tmp_path / "plain"
    extended = tmp_path / "extended"
    first = subprocess.run(command(plain, candidate), capture_output=True, text=True)
    second = subprocess.run([
        *command(extended, candidate), "--answer-alternatives", str(REFERENCES),
    ], capture_output=True, text=True)
    assert first.returncode == second.returncode == expected, second.stderr
    before = json.loads((plain / "report.json").read_text())
    after = json.loads((extended / "report.json").read_text())
    assert after.pop("report_schema_version") == 2
    after.pop("diagnostics")
    before.pop("report_schema_version")
    assert before == after


def test_bad_optional_references_return_input_error_without_report(tmp_path):
    bad = tmp_path / "references.json"
    bad.write_text("{}")
    output = tmp_path / "reports"
    process = subprocess.run([
        *command(output, CANDIDATE), "--answer-alternatives", str(bad),
    ], capture_output=True, text=True)
    assert process.returncode == 2
    assert str(bad) in process.stderr
    assert "reference case coverage mismatch" in process.stderr
    assert not output.exists()
