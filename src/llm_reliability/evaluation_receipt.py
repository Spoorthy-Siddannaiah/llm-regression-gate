"""Compact reproducible evidence identifiers, never raw answers or source passages."""
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from llm_reliability.models import Contract, Identifier
from llm_reliability.provenance import SHA256


class EvaluationReceipt(Contract):
    receipt_version: Literal[1] = 1
    input_sha256: dict[str, SHA256]
    evaluator_version: Identifier
    evaluator_source_sha256: dict[str, SHA256]
    policy_version: Identifier
    code_target_validation: Literal['not_requested', 'matched']

    @model_validator(mode='after')
    def consistent_inputs(self):
        if not {'dataset', 'baseline', 'candidate'} <= self.input_sha256.keys():
            raise ValueError('receipt requires dataset, baseline, and candidate hashes')
        if self.code_target_validation == 'matched' and 'expected_candidate_code' not in self.input_sha256:
            raise ValueError('matched target requires expected snapshot hash')
        return self


def input_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


def evaluator_hashes() -> dict[str, str]:
    package = Path(__file__).resolve().parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(package.glob('*.py'))}
