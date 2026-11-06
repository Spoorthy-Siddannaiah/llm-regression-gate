import json
from pathlib import Path
import shutil

import pytest

from llm_reliability.cli import main
from llm_reliability.loading import InputLoadError, load_comparison


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def files(tmp_path):
    dataset = tmp_path / "dataset.json"
    sources = tmp_path / "sources.json"
    shutil.copyfile(ROOT / "datasets/squad/v1/dataset.json", dataset)
    shutil.copyfile(ROOT / "datasets/squad/v1/sources.json", sources)
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    shutil.copytree(ROOT / "recordings/squad/llama3.2-bm25-v1", baseline)
    shutil.copytree(ROOT / "recordings/squad/llama3.2-bm25-top1-v1", candidate)
    return dataset, sources, baseline, candidate


def load(files, **kwargs):
    dataset, sources, baseline, candidate = files
    return load_comparison(dataset, baseline / "recording.json", candidate / "recording.json", **kwargs)


def change_json(path, change):
    payload = json.loads(path.read_text())
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_actual_manifests_validate_with_changed_retrieval_configuration(files):
    comparison = load(files, sources_path=files[1], require_manifests=True)
    assert comparison.baseline.configuration.retrieval_version == "bm25-v1-top3"
    assert comparison.candidate.configuration.retrieval_version == "bm25-v1-top1"
    assert len(comparison.candidate.responses) == 25


def test_sources_default_to_dataset_sibling(files):
    assert len(load(files).dataset.cases) == 25


@pytest.mark.parametrize("target", ["dataset", "sources", "recording", "evidence"])
def test_changed_bytes_rejected_even_with_same_version_labels(files, target):
    dataset, sources, _, candidate = files
    if target == "dataset":
        path = dataset
        change_json(path, lambda value: value["cases"][0].update(question="Changed question?"))
    elif target == "sources":
        path = sources
        change_json(path, lambda value: value.update({next(iter(value)): "Changed passage"}))
    elif target == "recording":
        path = candidate / "recording.json"
        change_json(path, lambda value: value["responses"][0].update(answer="Changed answer"))
    else:
        path = candidate / "evidence/001.response.json"
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(InputLoadError) as caught:
        load(files)
    assert "SHA-256 mismatch" in str(caught.value)
    assert str(path.resolve()) in str(caught.value)


@pytest.mark.parametrize("field, value, expected", [
    ("scope", "smoke_subset", "scope"),
    ("status", "incomplete", "status"),
    ("manifest_version", 2, "manifest_version"),
    ("recording_id", "another-run", "recording_id"),
    ("case_count", 1, "case_count"),
    ("prompt_version", "changed-prompt", "prompt_version"),
    ("retrieval_top_k", 2, "retrieval_top_k"),
])
def test_incompatible_manifest_fields_are_actionable(files, field, value, expected):
    path = files[3] / "manifest.json"
    change_json(path, lambda manifest: manifest.update({field: value}))
    with pytest.raises(InputLoadError) as caught:
        load(files)
    assert str(path) in str(caught.value)
    assert expected in str(caught.value)


def test_model_digest_must_match_recording_configuration(files):
    path = files[3] / "manifest.json"
    change_json(path, lambda manifest: manifest["model"].update(digest="0" * 64))
    with pytest.raises(InputLoadError, match="model.digest/name"):
        load(files)


def test_missing_required_recording_hash_is_an_error(files):
    path = files[3] / "manifest.json"
    change_json(path, lambda manifest: manifest["artifact_sha256"].pop("recording.json"))
    with pytest.raises(InputLoadError, match="missing required entries.*recording.json"):
        load(files)


@pytest.mark.parametrize("name", ["../outside.txt", "/tmp/outside.txt", "evidence\\outside.txt"])
def test_manifest_artifact_paths_cannot_escape_recording_directory(files, name):
    path = files[3] / "manifest.json"
    change_json(path, lambda manifest: manifest["artifact_sha256"].update({name: "0" * 64}))
    with pytest.raises(InputLoadError, match="unsafe relative path"):
        load(files)


def test_symlink_escape_is_rejected(files, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("outside recording")
    link = files[3] / "evidence/outside.txt"
    link.symlink_to(outside)
    change_json(files[3] / "manifest.json", lambda manifest: manifest["artifact_sha256"].update({
        "evidence/outside.txt": "0" * 64,
    }))
    with pytest.raises(InputLoadError, match="escapes recording directory"):
        load(files)


@pytest.mark.parametrize("which", ["one", "both"])
def test_missing_manifest_cannot_silently_downgrade_digest_recordings(files, which):
    (files[3] / "manifest.json").unlink()
    if which == "both":
        (files[2] / "manifest.json").unlink()
    with pytest.raises(InputLoadError, match="provenance.*manifest.json"):
        load(files)


def test_missing_evidence_is_an_input_error(files):
    (files[3] / "evidence/001.response.json").unlink()
    with pytest.raises(InputLoadError, match="001.response.json"):
        load(files)


def test_invalid_manifest_hash_format_is_an_error(files):
    path = files[3] / "manifest.json"
    change_json(path, lambda manifest: manifest["input_sha256"].update(sources="not-a-sha256"))
    with pytest.raises(InputLoadError, match="input_sha256.sources"):
        load(files)


def test_stale_input_cli_exits_two_before_scoring_or_reports(files, tmp_path, monkeypatch, capsys):
    dataset, sources, baseline, candidate = files
    sources.write_bytes(sources.read_bytes() + b"\n")
    output = tmp_path / "reports"

    def must_not_score(*args, **kwargs):
        pytest.fail("stale inputs reached scoring")

    monkeypatch.setattr("llm_reliability.cli.compare_and_gate", must_not_score)
    assert main([
        "--dataset", str(dataset), "--sources", str(sources), "--require-manifests",
        "--baseline", str(baseline / "recording.json"),
        "--candidate", str(candidate / "recording.json"), "--output-dir", str(output),
    ]) == 2
    assert "input_sha256.sources" in capsys.readouterr().err
    assert not output.exists()


def test_explicit_requirement_rejects_synthetic_inputs_without_manifests():
    with pytest.raises(InputLoadError, match="manifest.json"):
        load_comparison(
            ROOT / "datasets/support_policy/v1/dataset.json",
            ROOT / "recordings/baseline.synthetic.v1.json",
            ROOT / "recordings/candidate.synthetic.v1.json", require_manifests=True,
        )
