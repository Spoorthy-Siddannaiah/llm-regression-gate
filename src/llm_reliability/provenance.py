"""Integrity checks for completed local-Ollama recording manifests (schema v1)."""

import hashlib
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from llm_reliability.models import Identifier, Recording
from llm_reliability.retrieval import RetrievalSettings
from llm_reliability.run_provenance import CodeProvenance


SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ManifestFields(BaseModel):
    # Existing manifests include extra run evidence; validate the fields consumed here.
    model_config = ConfigDict(strict=True, extra="ignore")


class InputHashes(ManifestFields):
    dataset: SHA256
    sources: SHA256


class ModelIdentity(ManifestFields):
    name: Identifier
    digest: SHA256


class RecordingManifest(ManifestFields):
    manifest_version: int = Field(ge=1, le=1)
    status: Literal["completed_not_promoted"]
    scope: Literal["full_dataset"]
    recording_id: Identifier
    case_count: int = Field(gt=0)
    model: ModelIdentity
    prompt_version: Identifier
    retrieval_top_k: int = Field(gt=0)
    retrieval_settings: RetrievalSettings
    input_sha256: InputHashes
    artifact_sha256: dict[Identifier, SHA256] = Field(min_length=1)
    code_provenance: CodeProvenance | None = None


def _check_hash(path: Path, expected: str, label: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"{label}: SHA-256 mismatch for {path}; input or recording is stale/changed")


def validate_recording_manifest(
    manifest: RecordingManifest, *, manifest_path: Path, recording_path: Path,
    dataset_path: Path, sources_path: Path, recording: Recording,
) -> None:
    """Validate local files read-only; hashes are integrity checks, not signatures."""
    if manifest.recording_id != recording.recording_id:
        raise ValueError("recording_id does not match recording")
    if manifest.case_count != len(recording.responses):
        raise ValueError("case_count does not match recording responses")
    expected_model = f"{manifest.model.name}@sha256:{manifest.model.digest}"
    if recording.configuration.model_version != expected_model:
        raise ValueError("model.digest/name does not match configuration.model_version")
    if manifest.prompt_version != recording.configuration.prompt_version:
        raise ValueError("prompt_version does not match recording configuration")
    expected_retrieval = f"{manifest.retrieval_settings.retriever_version}-top{manifest.retrieval_top_k}"
    if recording.configuration.retrieval_version != expected_retrieval:
        raise ValueError("retrieval_top_k/settings do not match configuration.retrieval_version")

    _check_hash(dataset_path, manifest.input_sha256.dataset, "input_sha256.dataset")
    _check_hash(sources_path, manifest.input_sha256.sources, "input_sha256.sources")
    root = manifest_path.parent.resolve()
    if manifest.code_provenance is None and (
        "code-provenance.json" in manifest.artifact_sha256 or (root / "code-provenance.json").exists()
    ):
        raise ValueError("code_provenance metadata missing for code-provenance.json")
    relative_recording = recording_path.resolve().relative_to(root).as_posix()
    required = {relative_recording, "started.json"}
    if manifest.code_provenance is not None:
        required.add("code-provenance.json")
    for index in range(1, manifest.case_count + 1):
        required.update({f"evidence/{index:03d}.request.json", f"evidence/{index:03d}.response.json"})
    missing = required - manifest.artifact_sha256.keys()
    if missing:
        raise ValueError(f"artifact_sha256 missing required entries: {sorted(missing)}")
    for name, digest in manifest.artifact_sha256.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError(f"artifact_sha256 has unsafe relative path: {name!r}")
        target = (root / name).resolve()
        if not target.is_relative_to(root) or target == root:
            raise ValueError(f"artifact_sha256 path escapes recording directory: {name!r}")
        _check_hash(target, digest, f"artifact_sha256[{name!r}]")
    if manifest.code_provenance is not None:
        snapshot_path = root / "code-provenance.json"
        snapshot = CodeProvenance.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
        if snapshot != manifest.code_provenance:
            raise ValueError("code_provenance does not match code-provenance.json")
