"""Read-only JSON loading with file-aware errors; no evaluation or scoring."""

from pathlib import Path
import json

from pydantic import BaseModel, ValidationError

from llm_reliability.gates import GatePolicy, GatePolicyDocument, GatePolicyV2
from llm_reliability.models import ComparisonInput, Dataset, Recording
from llm_reliability.runner import EvaluationSettings
from llm_reliability.retrieval import SourceCorpus
from llm_reliability.provenance import RecordingManifest, validate_recording_manifest
from llm_reliability.run_provenance import CodeProvenance, verify_candidate_code


class InputLoadError(ValueError):
    """An evaluation input could not be read or validated."""


def _validation_details(error: ValidationError) -> str:
    # Do not echo entire input payloads into logs or future CLI output.
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or '<root>'}: {item['msg']}"
        for item in error.errors(include_input=False, include_url=False)
    )


def _load[T: BaseModel](path: str | Path, model: type[T]) -> T:
    source = Path(path)
    try:
        content = source.read_bytes()
    except (OSError, UnicodeError) as error:
        raise InputLoadError(f"{source}: cannot read UTF-8 input: {error}") from error
    return parse_input_bytes(content, model, source=source)


def parse_input_bytes[T: BaseModel](content: bytes, model: type[T], *, source: str | Path) -> T:
    """Validate the exact captured bytes; callers may hash and retain this snapshot."""
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise InputLoadError(f"{source}: cannot read UTF-8 input") from error
    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                # Keys can themselves contain sensitive values. Do not echo them.
                raise InputLoadError(f"{source}: duplicate JSON object key (ambiguous input)")
            result[key] = value
        return result
    def reject_constant(value: str) -> None:
        raise InputLoadError(f"{source}: nonstandard JSON numeric constant")
    try:
        json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise InputLoadError(f"{source}: invalid JSON at line {error.lineno}, column {error.colno}") from error
    try:
        return model.model_validate_json(text)
    except ValidationError as error:
        raise InputLoadError(f"{source}: {_validation_details(error)}") from error


def load_dataset(path: str | Path) -> Dataset:
    return _load(path, Dataset)


def load_recording(path: str | Path) -> Recording:
    return _load(path, Recording)


def load_corpus(path: str | Path) -> SourceCorpus:
    return _load(path, SourceCorpus)


def validate_source_references(dataset: Dataset, corpus: SourceCorpus) -> None:
    """Only labelled relevance requires membership; observations may contain unknown IDs."""
    for index, case in enumerate(dataset.cases):
        missing = set(case.relevant_source_ids) - corpus.root.keys()
        if missing:
            raise InputLoadError(f"cases.{index}.relevant_source_ids: {len(missing)} referenced source ID(s) absent from corpus")


def load_gate_policy(path: str | Path) -> GatePolicy | GatePolicyV2:
    return _load(path, GatePolicyDocument).root


def load_evaluation_settings(path: str | Path) -> EvaluationSettings:
    return _load(path, EvaluationSettings)


def load_comparison(
    dataset_path: str | Path,
    baseline_path: str | Path,
    candidate_path: str | Path,
    *, sources_path: str | Path | None = None, require_manifests: bool = False,
    expected_candidate_code: str | Path | None = None,
) -> ComparisonInput:
    dataset = load_dataset(dataset_path)
    baseline = load_recording(baseline_path)
    candidate = load_recording(candidate_path)
    corpus_path = Path(sources_path) if sources_path is not None else Path(dataset_path).with_name("sources.json")
    if sources_path is not None or corpus_path.exists():
        try:
            validate_source_references(dataset, load_corpus(corpus_path))
        except InputLoadError as error:
            raise InputLoadError(f"dataset={dataset_path}, corpus={corpus_path}: {error}") from error
    try:
        comparison = ComparisonInput(dataset=dataset, baseline=baseline, candidate=candidate)
    except ValidationError as error:
        raise InputLoadError(
            f"Comparison inputs (dataset={dataset_path}, baseline={baseline_path}, "
            f"candidate={candidate_path}): {_validation_details(error)}"
        ) from error
    manifests = [Path(path).parent / "manifest.json" for path in (baseline_path, candidate_path)]
    needs_manifests = (
        require_manifests or sources_path is not None or expected_candidate_code is not None
        or any(path.exists() for path in manifests)
        or any("@sha256:" in item.configuration.model_version for item in (baseline, candidate))
    )
    if needs_manifests:
        expected_code = _load(expected_candidate_code, CodeProvenance) if expected_candidate_code is not None else None
        corpus_path = Path(sources_path) if sources_path is not None else Path(dataset_path).with_name("sources.json")
        for role, path, manifest_path, recording in zip(
            ("baseline", "candidate"), (baseline_path, candidate_path), manifests,
            (baseline, candidate), strict=True,
        ):
            try:
                manifest = _load(manifest_path, RecordingManifest)
                validate_recording_manifest(
                    manifest, manifest_path=manifest_path, recording_path=Path(path),
                    dataset_path=Path(dataset_path), sources_path=corpus_path, recording=recording,
                )
                if role == "candidate" and expected_code is not None:
                    if manifest.code_provenance is None:
                        raise ValueError("candidate has no code_provenance; cannot verify requested freshness")
                    try:
                        verify_candidate_code(manifest.code_provenance, expected_code)
                    except ValueError as error:
                        raise ValueError(f"expected candidate code ({expected_candidate_code}): {error}") from error
            except (OSError, ValueError) as error:
                raise InputLoadError(f"{role} provenance ({manifest_path}): {error}") from error
    return comparison
