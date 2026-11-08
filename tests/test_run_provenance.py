import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from llm_reliability.loading import InputLoadError, load_comparison
from llm_reliability.run_provenance import CodeProvenance, capture_code_provenance, verify_generation_sources


@pytest.fixture
def source_tree(tmp_path):
    root = tmp_path / "project"
    for name in ("scripts/record_ollama.py", "src/llm_reliability/generation.py", "pyproject.toml", "uv.lock"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example source\n")
    return root


@pytest.mark.parametrize("dirty", [False, True])
def test_capture_git_revision_dirty_state_and_hashes(source_tree, monkeypatch, dirty):
    def fake_git(command, **kwargs):
        assert kwargs["cwd"] == source_tree
        assert command[0] == "git"
        return SimpleNamespace(stdout="a" * 40 + "\n" if command[1] == "rev-parse" else " M example.py\n" if dirty else "")

    monkeypatch.setattr("llm_reliability.run_provenance.subprocess.run", fake_git)
    snapshot = capture_code_provenance(source_tree)
    assert snapshot.git_commit == "a" * 40
    assert snapshot.working_tree_dirty is dirty
    assert snapshot.git_status == "available"
    for name, digest in snapshot.source_sha256.items():
        assert not Path(name).is_absolute()
        assert digest == hashlib.sha256((source_tree / name).read_bytes()).hexdigest()
    verify_generation_sources(snapshot, source_tree)


def test_unavailable_git_is_explicit_not_fabricated(source_tree, monkeypatch):
    def no_git(*args, **kwargs):
        raise FileNotFoundError("git unavailable")

    monkeypatch.setattr("llm_reliability.run_provenance.subprocess.run", no_git)
    snapshot = capture_code_provenance(source_tree)
    assert snapshot.git_status == "unavailable"
    assert snapshot.git_commit is snapshot.working_tree_dirty is None
    assert snapshot.source_sha256


def test_git_status_failure_is_not_reported_as_clean(source_tree, monkeypatch):
    def fake_git(command, **kwargs):
        if command[1] == "rev-parse":
            return SimpleNamespace(stdout="a" * 40)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr("llm_reliability.run_provenance.subprocess.run", fake_git)
    snapshot = capture_code_provenance(source_tree)
    assert snapshot.git_status == "unavailable"
    assert snapshot.working_tree_dirty is None


def test_source_symlink_cannot_escape_project(source_tree, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("outside test content")
    (source_tree / "src/llm_reliability/outside.py").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes project"):
        capture_code_provenance(source_tree)


@pytest.mark.parametrize("change", ["edit", "add", "delete"])
def test_mid_run_source_changes_prevent_completion(source_tree, change):
    snapshot = capture_code_provenance(source_tree)
    if change == "edit":
        (source_tree / "src/llm_reliability/generation.py").write_text("changed")
    elif change == "add":
        (source_tree / "src/llm_reliability/new.py").write_text("new code")
    else:
        (source_tree / "scripts/record_ollama.py").unlink()
    with pytest.raises((ValueError, OSError)):
        verify_generation_sources(snapshot, source_tree)


@pytest.mark.parametrize("field, value", [
    ("git_commit", None), ("working_tree_dirty", None),
    ("git_commit", "not-a-commit"), ("working_tree_dirty", "false"),
    ("source_sha256", {"../outside.py": "0" * 64}),
    ("source_sha256", {"file.py": "not-a-hash"}),
])
def test_invalid_code_metadata_is_rejected(field, value):
    data = {
        "git_status": "available", "git_commit": "a" * 40,
        "working_tree_dirty": False, "source_sha256": {"file.py": "0" * 64},
    }
    data[field] = value
    with pytest.raises(ValidationError):
        CodeProvenance.model_validate(data)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("problem", [None, "mismatch", "missing_hash", "missing_metadata"])
def test_optional_metadata_validation_preserves_historical_replay(tmp_path, problem):
    run = tmp_path / "run"
    shutil.copytree(ROOT / "recordings/squad/llama3.2-bm25-v1", run)
    # Historical source hashes need not match today's checkout to replay old outputs.
    snapshot = CodeProvenance(
        git_status="available", git_commit="a" * 40, working_tree_dirty=True,
        source_sha256={"scripts/record_ollama.py": "0" * 64},
    )
    path = run / "code-provenance.json"
    path.write_text(snapshot.model_dump_json())
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["code_provenance"] = snapshot.model_dump(mode="json")
    manifest["artifact_sha256"]["code-provenance.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if problem == "mismatch":
        manifest["code_provenance"]["git_commit"] = "b" * 40
    elif problem == "missing_hash":
        manifest["artifact_sha256"].pop("code-provenance.json")
    elif problem == "missing_metadata":
        manifest.pop("code_provenance")
    manifest_path.write_text(json.dumps(manifest))
    args = (ROOT / "datasets/squad/v1/dataset.json", run / "recording.json", run / "recording.json")
    if problem is None:
        assert len(load_comparison(*args).baseline.responses) == 25
    else:
        with pytest.raises(InputLoadError, match="code.provenance"):
            load_comparison(*args)
