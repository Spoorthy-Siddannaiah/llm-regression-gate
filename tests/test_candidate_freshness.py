import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from llm_reliability.cli import main
from llm_reliability.loading import InputLoadError, load_comparison
from llm_reliability.run_provenance import CodeProvenance, verify_candidate_code


ROOT = Path(__file__).resolve().parents[1]


def snapshot(commit="b", digest="1", dirty=False):
    return CodeProvenance(
        git_status="available", git_commit=commit * 40, working_tree_dirty=dirty,
        source_sha256={"src/llm_reliability/generation.py": digest * 64},
    )


def attach(run, value):
    # Test metadata only; actual tracked model recordings are never edited.
    path = run / "code-provenance.json"
    path.write_text(value.model_dump_json())
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["code_provenance"] = value.model_dump(mode="json")
    manifest["artifact_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


@pytest.fixture
def files(tmp_path):
    baseline, candidate = tmp_path / "baseline", tmp_path / "candidate"
    shutil.copytree(ROOT / "recordings/squad/llama3.2-bm25-v1", baseline)
    shutil.copytree(ROOT / "recordings/squad/llama3.2-bm25-top1-v1", candidate)
    attach(candidate, snapshot(dirty=True))
    expected = tmp_path / "expected.json"
    expected.write_text(snapshot(dirty=False).model_dump_json())
    return baseline, candidate, expected


@pytest.mark.parametrize("problem", ["commit", "changed", "added", "missing", "expected_unavailable", "observed_unavailable"])
def test_freshness_rejects_wrong_revision_or_source_set(problem):
    observed, expected = snapshot(), snapshot()
    if problem == "commit":
        observed.git_commit = "a" * 40
    elif problem == "changed":
        observed.source_sha256[next(iter(observed.source_sha256))] = "2" * 64
    elif problem == "added":
        observed.source_sha256["new.py"] = "2" * 64
    elif problem == "missing":
        expected.source_sha256["extra.py"] = "2" * 64
    else:
        unavailable = CodeProvenance(
            git_status="unavailable", git_commit=None, working_tree_dirty=None,
            source_sha256=expected.source_sha256,
        )
        if problem == "expected_unavailable":
            expected = unavailable
        else:
            observed = unavailable
    with pytest.raises(ValueError, match="candidate|freshness"):
        verify_candidate_code(observed, expected)


def test_dirty_flag_difference_is_informational():
    verify_candidate_code(snapshot(dirty=True), snapshot(dirty=False))


@pytest.mark.parametrize("baseline_has_code", [False, True])
def test_freshness_applies_to_candidate_only(files, baseline_has_code):
    baseline, candidate, expected = files
    if baseline_has_code:
        attach(baseline, snapshot(commit="a", digest="9"))
    result = load_comparison(
        ROOT / "datasets/squad/v1/dataset.json", baseline / "recording.json", candidate / "recording.json",
        expected_candidate_code=expected,
    )
    assert len(result.candidate.responses) == 25


def test_legacy_candidate_remains_replayable_but_cannot_satisfy_freshness(files):
    baseline, _, expected = files
    args = (ROOT / "datasets/squad/v1/dataset.json", baseline / "recording.json", baseline / "recording.json")
    assert len(load_comparison(*args).candidate.responses) == 25
    with pytest.raises(InputLoadError, match="candidate has no code_provenance"):
        load_comparison(*args, expected_candidate_code=expected)


def arguments(files, output):
    baseline, candidate, expected = files
    return [
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--baseline", str(baseline / "recording.json"), "--candidate", str(candidate / "recording.json"),
        "--expected-candidate-code", str(expected), "--output-dir", str(output),
    ]


def test_stale_candidate_cli_exits_two_before_scoring(files, tmp_path, monkeypatch, capsys):
    files[2].write_text(snapshot(digest="8").model_dump_json())
    output = tmp_path / "reports"

    def must_not_score(*args, **kwargs):
        pytest.fail("stale candidate reached scoring")

    monkeypatch.setattr("llm_reliability.cli.compare_and_gate", must_not_score)
    assert main(arguments(files, output)) == 2
    error = capsys.readouterr().err
    assert "candidate source SHA-256 mismatch" in error
    assert str(files[2]) in error
    assert not output.exists()


def test_matching_freshness_preserves_quality_result(files, tmp_path):
    flagged, plain = tmp_path / "flagged", tmp_path / "plain"
    args = arguments(files, flagged)
    assert main(args) == 1
    index = args.index("--expected-candidate-code")
    del args[index:index + 2]
    args[-1] = str(plain)
    assert main(args) == 1
    flagged_report = json.loads((flagged / "report.json").read_text())
    plain_report = json.loads((plain / "report.json").read_text())
    assert flagged_report.pop("provenance")["code_target_validation"] == "matched"
    assert plain_report.pop("provenance")["code_target_validation"] == "not_requested"
    assert flagged_report == plain_report


@pytest.mark.parametrize("bad", ["missing", "malformed"])
def test_invalid_expected_snapshot_is_actionable(files, tmp_path, bad, capsys):
    if bad == "missing":
        files[2].unlink()
    else:
        files[2].write_text("{}")
    output = tmp_path / "reports"
    assert main(arguments(files, output)) == 2
    assert str(files[2]) in capsys.readouterr().err
    assert not output.exists()


def test_snapshot_script_captures_without_overwriting(tmp_path):
    output = tmp_path / "expected.json"
    command = [sys.executable, str(ROOT / "scripts/capture_code_provenance.py"), "--output", str(output)]
    process = subprocess.run(command, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    value = CodeProvenance.model_validate_json(output.read_text())
    assert value.git_status == "available"
    assert "scripts/record_ollama.py" in value.source_sha256
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode == 2
    assert output.read_bytes() == before
