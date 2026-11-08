"""Source-tree evidence for future generation runs; no Git writes or network calls."""

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from llm_reliability.models import Contract


class CodeProvenance(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
    git_status: Literal["available", "unavailable"]
    git_commit: Annotated[str, StringConstraints(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")] | None
    working_tree_dirty: bool | None
    source_sha256: dict[str, Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_metadata(self) -> Self:
        available = self.git_status == "available"
        if available != (self.git_commit is not None and self.working_tree_dirty is not None):
            raise ValueError("available Git metadata requires both commit and dirty state")
        if not available and (self.git_commit is not None or self.working_tree_dirty is not None):
            raise ValueError("unavailable Git metadata must use null commit and dirty state")
        for name in self.source_sha256:
            path = PurePosixPath(name)
            if not name or path.is_absolute() or ".." in path.parts or "\\" in name or path == PurePosixPath("."):
                raise ValueError(f"invalid project-relative source path: {name!r}")
        return self


def _source_hashes(root: Path) -> dict[str, str]:
    root = root.resolve()
    package = root / "src/llm_reliability"
    files = [root / "scripts/record_ollama.py", root / "pyproject.toml", root / "uv.lock"]
    sources = sorted(package.rglob("*.py"))
    if not sources:
        raise ValueError("generation source package is missing")
    files.extend(sources)
    result = {}
    for path in files:
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"generation source escapes project: {path.name}")
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def capture_code_provenance(root: Path) -> CodeProvenance:
    hashes = _source_hashes(root)
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=root,
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root,
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout)
    except (OSError, subprocess.SubprocessError):
        return CodeProvenance(
            git_status="unavailable", git_commit=None, working_tree_dirty=None,
            source_sha256=hashes,
        )
    return CodeProvenance(
        git_status="available", git_commit=revision, working_tree_dirty=dirty,
        source_sha256=hashes,
    )


def verify_generation_sources(snapshot: CodeProvenance, root: Path) -> None:
    """Prevent completion if covered source files change, appear, or disappear mid-run."""
    if _source_hashes(root) != snapshot.source_sha256:
        raise ValueError("generation source files changed during run; recording not completed")


def verify_candidate_code(observed: CodeProvenance, expected: CodeProvenance) -> None:
    """Opt-in equality against a caller-selected revision/source snapshot, not current HEAD.

    Dirty flags are informational: writing run artifacts may change Git status
    without changing covered code. Full covered hashes must still match exactly.
    """
    if expected.git_status != "available" or observed.git_status != "available":
        raise ValueError("candidate freshness requires available Git revisions in both snapshots")
    if observed.git_commit != expected.git_commit:
        raise ValueError("candidate git_commit does not match expected code snapshot")
    expected_names, observed_names = set(expected.source_sha256), set(observed.source_sha256)
    if expected_names != observed_names:
        raise ValueError(
            f"candidate source file set mismatch: missing={sorted(expected_names - observed_names)}, "
            f"unexpected={sorted(observed_names - expected_names)}"
        )
    changed = sorted(name for name in expected_names if observed.source_sha256[name] != expected.source_sha256[name])
    if changed:
        raise ValueError(f"candidate source SHA-256 mismatch: {changed}")
