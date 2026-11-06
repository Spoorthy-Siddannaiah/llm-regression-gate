import json
from pathlib import Path

import pytest

from llm_reliability.gates import compare_and_gate
from llm_reliability.loading import load_comparison
from llm_reliability.reports import ReportWriteError, render_json, render_markdown, write_reports


@pytest.fixture
def result():
    root = Path(__file__).resolve().parents[1]
    inputs = load_comparison(
        root / "datasets/support_policy/v1/dataset.json",
        root / "recordings/baseline.synthetic.v1.json",
        root / "recordings/candidate.synthetic.v2.json",
    )
    return compare_and_gate(inputs)


def test_json_preserves_full_result_and_report_version(result):
    payload = json.loads(render_json(result))
    assert payload.pop("report_schema_version") == 1
    assert payload == result.model_dump(mode="json")
    assert payload["passed"] is False
    assert payload["metrics"][0]["delta"] == -0.5
    assert payload["evaluation"]["candidate"]["cases"][0]["retrieval_recall_at_k"] == 1.0


def test_markdown_contains_decision_provenance_policy_and_case_evidence(result):
    text = render_markdown(result)
    assert "**Gate: FAIL**" in text
    assert "1.000000 | 0.500000 | -0.500000" in text
    assert "require critical facts: True" in text
    assert "refund\\-window" in text
    assert "30 days; proof of purchase" in text
    assert "synthetic\\-baseline\\-v1" in text
    assert "synthetic\\-candidate\\-v2" in text
    assert "deterministic\\-v1" in text
    assert "synthetic fixtures" in text
    assert "do not establish semantic correctness" in text
    assert r"\('30 days', 'proof of purchase'\)" in text


def test_passing_decision_is_rendered_without_failures(result):
    result.failures = ()
    assert json.loads(render_json(result))["passed"] is True
    assert "**Gate: PASS**" in render_markdown(result)
    assert "## Gate failures\n\nNone." in render_markdown(result)


def test_markdown_escapes_fixture_content(result):
    result.evaluation.dataset_id = '<script>alert(1)</script>|[link](url)\n# heading'
    text = render_markdown(result)
    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert r"\|\[link\]\(url\)" in text
    assert "<br>\\# heading" in text


def test_rendering_is_repeatable_and_does_not_mutate_result(result):
    before = result.model_dump_json()
    assert render_json(result) == render_json(result)
    assert render_markdown(result) == render_markdown(result)
    assert result.model_dump_json() == before


def test_writes_utf8_reports_with_matching_contents(result, tmp_path):
    result.evaluation.dataset_id = "support-überprüfung"
    json_path, md_path = write_reports(result, tmp_path / "nested" / "run-1")
    assert json_path.read_text(encoding="utf-8") == render_json(result)
    assert md_path.read_text(encoding="utf-8") == render_markdown(result)
    assert "überprüfung" in json_path.read_text(encoding="utf-8")


def test_existing_output_is_never_overwritten(result, tmp_path):
    directory = tmp_path / "run"
    paths = write_reports(result, directory)
    original = [path.read_bytes() for path in paths]
    with pytest.raises(ReportWriteError, match="never overwritten"):
        write_reports(result, directory)
    assert [path.read_bytes() for path in paths] == original


def test_invalid_destination_identifies_directory(result, tmp_path):
    parent = tmp_path / "file"
    parent.write_text("preserve")
    destination = parent / "reports"
    with pytest.raises(ReportWriteError) as caught:
        write_reports(result, destination)
    assert str(destination) in str(caught.value)
    assert parent.read_text() == "preserve"


def test_partial_write_failure_is_explicit(result, tmp_path, monkeypatch):
    original_open = Path.open

    def fail_markdown(path, *args, **kwargs):
        if path.name == "report.md":
            raise OSError("simulated disk error")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_markdown)
    destination = tmp_path / "partial"
    with pytest.raises(ReportWriteError, match="partial artifacts"):
        write_reports(result, destination)
    assert (destination / "report.json").exists()
    assert not (destination / "report.md").exists()
