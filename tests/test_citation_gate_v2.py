import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from llm_reliability.gates import (
    GatePolicy, GatePolicyV2, GateResultV2, UnknownCitationLimits, compare_and_gate,
)
from llm_reliability.loading import InputLoadError, load_comparison, load_corpus, load_gate_policy
from llm_reliability.reports import render_json, render_markdown


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def experiment():
    directory = ROOT / "datasets/support_policy/v1"
    inputs = load_comparison(
        directory / "dataset.json", ROOT / "recordings/baseline.synthetic.v1.json",
        ROOT / "recordings/candidate.synthetic.v1.json",
    )
    sources = directory / "sources.json"
    return inputs, load_corpus(sources), hashlib.sha256(sources.read_bytes()).hexdigest()


def evaluate(experiment, **limits):
    inputs, corpus, digest = experiment
    return compare_and_gate(
        inputs, corpus=corpus, corpus_sha256=digest,
        policy=GatePolicyV2(unknown_citations=UnknownCitationLimits(**limits)),
    )


def test_unknown_ids_enforced_without_diagnostic_flag(experiment):
    inputs, _, _ = experiment
    inputs.candidate.responses[0].cited_source_ids.append("unknown-document")
    before = inputs.model_dump_json()
    result = evaluate(experiment)
    assert isinstance(result, GateResultV2)
    assert not result.passed
    assert {failure.code for failure in result.failures} == {
        "unknown_citation_limit", "unknown_citation_increase",
    }
    assert all("refund-window" in failure.message for failure in result.failures)
    assert result.citation_existence_gate.candidate_unknown_count == 1
    payload = json.loads(render_json(result))
    assert payload["report_schema_version"] == 4
    assert payload["policy"]["unknown_citations"]["max_candidate_unknown"] == 0
    assert payload["citation_existence_gate"]["increase"] == 1
    assert "Enforced unknown-citation gate" in render_markdown(result)
    assert inputs.model_dump_json() == before


def test_inherited_unknown_id_fails_absolute_limit_only(experiment):
    inputs, _, _ = experiment
    for recording in (inputs.baseline, inputs.candidate):
        recording.responses[0].cited_source_ids.append("unknown-document")
    result = evaluate(experiment)
    assert [failure.code for failure in result.failures] == ["unknown_citation_limit"]
    assert result.citation_existence_gate.increase == 0


def test_existing_unlabelled_source_is_allowed(experiment):
    inputs, _, _ = experiment
    inputs.candidate.responses[0].cited_source_ids.append("support-hours-v1")
    assert evaluate(experiment).passed


def test_improved_unknown_count_passes(experiment):
    inputs, _, _ = experiment
    inputs.baseline.responses[0].cited_source_ids.append("unknown-document")
    result = evaluate(experiment)
    assert result.passed
    assert result.citation_existence_gate.increase == -1


@pytest.mark.parametrize("maximum, increase, passes", [(2, 1, True), (1, 1, False), (2, 0, False), (3, 2, True)])
def test_integer_thresholds_and_equality(experiment, maximum, increase, passes):
    inputs, _, _ = experiment
    inputs.baseline.responses[0].cited_source_ids.append("unknown-document")
    # Same ID in two separate requests counts as two occurrences, not one unique ID.
    for response in inputs.candidate.responses:
        response.cited_source_ids.append("unknown-document")
    result = evaluate(experiment, max_candidate_unknown=maximum, max_increase=increase)
    assert result.passed == passes
    assert result.citation_existence_gate.candidate_unknown_count == 2


def test_missing_citations_do_not_count_as_unknown_but_old_gate_still_checks_coverage(experiment):
    inputs, _, _ = experiment
    inputs.candidate.responses[0].cited_source_ids = []
    result = evaluate(experiment)
    assert result.citation_existence_gate.candidate_unknown_count == 0
    assert [failure.code for failure in result.failures] == ["excessive_drop"]


def test_v2_requires_corpus_while_v1_remains_default(experiment):
    inputs, _, _ = experiment
    with pytest.raises(ValueError, match="requires corpus"):
        compare_and_gate(inputs, policy=GatePolicyV2(unknown_citations=UnknownCitationLimits()))
    result = compare_and_gate(inputs)
    assert type(result.policy) is GatePolicy
    assert "citation_existence_gate" not in result.model_dump()
    assert json.loads(render_json(result))["report_schema_version"] == 4


@pytest.mark.parametrize("field", ["max_candidate_unknown", "max_increase"])
@pytest.mark.parametrize("value", [-1, True, 0.5, "1"])
def test_bad_count_limits_rejected(field, value):
    with pytest.raises(ValidationError):
        UnknownCitationLimits(**{field: value})


def test_policy_loading_is_explicit_and_preserves_legacy_default(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text('{"fact_coverage": {"minimum": 0.5}}')
    assert type(load_gate_policy(path)) is GatePolicy
    path.write_text('{"unknown_citations": {"max_candidate_unknown": 0}}')
    with pytest.raises(InputLoadError):
        load_gate_policy(path)  # v2 field cannot silently enable itself on v1.
    assert isinstance(load_gate_policy(ROOT / "configs/gate.citation-v2.json"), GatePolicyV2)
    path.write_text('{"policy_version": "deterministic-gate-v2"}')
    with pytest.raises(InputLoadError, match="unknown_citations"):
        load_gate_policy(path)


@pytest.mark.parametrize("candidate", ["llama3.2-bm25-v1", "llama3.2-bm25-top1-v1"])
@pytest.mark.parametrize("diagnostics", [False, True])
def test_real_cli_v2_explains_failure_and_keeps_schema_four(tmp_path, candidate, diagnostics):
    output = tmp_path / "report"
    command = [
        sys.executable, "-m", "llm_reliability", "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"), "--require-manifests",
        "--baseline", str(ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json"),
        "--candidate", str(ROOT / "recordings/squad" / candidate / "recording.json"),
        "--policy", str(ROOT / "configs/gate.citation-v2.json"), "--output-dir", str(output),
    ]
    if diagnostics:
        command += ["--citation-existence", "--answer-alternatives", str(ROOT / "datasets/squad/v1/references.json")]
    process = subprocess.run(command, capture_output=True, text=True)
    assert process.returncode == 1, process.stderr
    report = json.loads((output / "report.json").read_text())
    assert report["report_schema_version"] == 4
    codes = {failure["code"] for failure in report["failures"]}
    assert codes == ({"unknown_citation_limit"} if candidate == "llama3.2-bm25-v1" else {"excessive_drop"})
    assert report["citation_existence_gate"]["candidate_unknown_count"] == (1 if candidate == "llama3.2-bm25-v1" else 0)
    assert ("diagnostics" in report) == diagnostics
    artifact = json.loads((ROOT / "benchmarks/squad-citation-gate-v2.json").read_text())
    key = "baseline_self_check" if candidate == "llama3.2-bm25-v1" else "candidate_comparison"
    legacy = {name: value for name, value in report.items() if name not in ("diagnostics", "case_changes", "provenance")}
    legacy["report_schema_version"] = artifact[key]["report_schema_version"]
    assert legacy == artifact[key]
    assert "Enforced unknown-citation gate" in (output / "report.md").read_text()


def test_v2_known_good_fixture_passes_and_missing_corpus_is_error(tmp_path):
    command = [
        sys.executable, "-m", "llm_reliability", "--dataset", str(ROOT / "datasets/support_policy/v1/dataset.json"),
        "--baseline", str(ROOT / "recordings/baseline.synthetic.v1.json"),
        "--candidate", str(ROOT / "recordings/candidate.synthetic.v1.json"),
        "--policy", str(ROOT / "configs/gate.citation-v2.json"),
        "--output-dir", str(tmp_path / "good"),
    ]
    assert subprocess.run(command, capture_output=True).returncode == 0
    dataset = tmp_path / "dataset.json"
    dataset.write_bytes((ROOT / "datasets/support_policy/v1/dataset.json").read_bytes())
    command[command.index("--dataset") + 1] = str(dataset)
    command[-1] = str(tmp_path / "bad")
    process = subprocess.run(command, capture_output=True, text=True)
    assert process.returncode == 2
    assert "sources.json" in process.stderr
    assert not (tmp_path / "bad").exists()
