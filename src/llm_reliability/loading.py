"""Read-only JSON loading with file-aware errors; no evaluation or scoring."""

from pathlib import Path

from pydantic import BaseModel, ValidationError

from llm_reliability.gates import GatePolicy
from llm_reliability.models import ComparisonInput, Dataset, Recording
from llm_reliability.runner import EvaluationSettings


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
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise InputLoadError(f"{source}: cannot read UTF-8 input: {error}") from error
    try:
        return model.model_validate_json(content)
    except ValidationError as error:
        raise InputLoadError(f"{source}: {_validation_details(error)}") from error


def load_dataset(path: str | Path) -> Dataset:
    return _load(path, Dataset)


def load_recording(path: str | Path) -> Recording:
    return _load(path, Recording)


def load_gate_policy(path: str | Path) -> GatePolicy:
    return _load(path, GatePolicy)


def load_evaluation_settings(path: str | Path) -> EvaluationSettings:
    return _load(path, EvaluationSettings)


def load_comparison(
    dataset_path: str | Path,
    baseline_path: str | Path,
    candidate_path: str | Path,
) -> ComparisonInput:
    dataset = load_dataset(dataset_path)
    baseline = load_recording(baseline_path)
    candidate = load_recording(candidate_path)
    try:
        return ComparisonInput(dataset=dataset, baseline=baseline, candidate=candidate)
    except ValidationError as error:
        raise InputLoadError(
            f"Comparison inputs (dataset={dataset_path}, baseline={baseline_path}, "
            f"candidate={candidate_path}): {_validation_details(error)}"
        ) from error
