import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from llm_reliability.generation import MODEL_DIGEST
from llm_reliability.loading import load_comparison, load_dataset, load_recording


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json"


@pytest.fixture
def wrapper():
    spec = importlib.util.spec_from_file_location("local_candidate_workflow", ROOT / "scripts/run_local_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(output, top_k=3):
    return [
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"),
        "--baseline", str(BASELINE), "--policy", str(ROOT / "configs/gate.relative-only.v1.json"),
        "--settings", str(ROOT / "configs/evaluator.v1.json"),
        "--recording-id", "mocked-workflow-not-new-model-output", "--top-k", str(top_k),
        "--output-dir", str(output),
    ]


@pytest.mark.parametrize("top_k, expected", [(3, 0), (1, 1)])
def test_full_workflow_uses_real_recorder_with_mocked_model_and_real_comparison(
    wrapper, tmp_path, monkeypatch, top_k, expected,
):
    dataset = load_dataset(ROOT / "datasets/squad/v1/dataset.json")
    saved = load_recording(ROOT / "recordings/squad" / (
        "llama3.2-bm25-v1" if top_k == 3 else "llama3.2-bm25-top1-v1"
    ) / "recording.json")
    answers = {case.question: response for case, response in zip(dataset.cases, saved.responses, strict=True)}
    requests = []

    class MockOllama:
        def verify_model(self):
            return {"name": "llama3.2:latest", "digest": MODEL_DIGEST}

        def request(self, path, payload=None):
            if path != "/api/chat":
                return {"version": "mocked-no-model-service"}
            prompt = json.loads(payload["messages"][1]["content"])
            assert set(prompt) == {"question", "sources"}
            requests.append(prompt)
            answer = answers[prompt["question"]]
            return {
                "done": True, "done_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps({
                        "answer": answer.answer, "cited_source_ids": answer.cited_source_ids,
                    }),
                },
            }

    monkeypatch.setattr("llm_reliability.generation.LocalOllama", MockOllama)
    calls = []

    def run_stage(command, *, cwd, timeout):
        calls.append(command)
        if command[1].endswith("record_ollama.py"):
            with monkeypatch.context() as context:
                context.setattr(sys, "argv", command[1:])
                runpy.run_path(command[1], run_name="__main__")
            return 0
        assert "--expected-candidate-code" in command
        return subprocess.run(command, cwd=cwd, timeout=timeout, capture_output=True).returncode

    monkeypatch.setattr(wrapper, "_run", run_stage)
    baseline_before = BASELINE.read_bytes(), (BASELINE.parent / "manifest.json").read_bytes()
    output = tmp_path / "run"
    assert wrapper.main(arguments(output, top_k)) == expected
    assert len(requests) == 25 and len(calls) == 2
    assert all(len(prompt["sources"]) == top_k for prompt in requests)
    completed = json.loads((output / "completed.json").read_text())
    assert completed["exit_code"] == expected
    assert completed["baseline_promoted"] is False
    assert set(completed["report_sha256"]) == {"report.json", "report.md"}
    snapshot = json.loads((output / "expected-code.json").read_text())
    assert "scripts/run_local_candidate.py" in snapshot["source_sha256"]
    assert json.loads((output / "reports/report.json").read_text())["passed"] == (expected == 0)
    load_comparison(
        ROOT / "datasets/squad/v1/dataset.json", BASELINE, output / "candidate/recording.json",
        expected_candidate_code=output / "expected-code.json",
    )
    assert baseline_before == (BASELINE.read_bytes(), (BASELINE.parent / "manifest.json").read_bytes())


@pytest.mark.parametrize("status", [1, 2, "timeout"])
def test_generation_failure_never_reaches_comparison(wrapper, tmp_path, monkeypatch, status):
    calls = []

    def fail(command, **kwargs):
        calls.append(command)
        if status == "timeout":
            raise subprocess.TimeoutExpired(command, 3600)
        return status

    monkeypatch.setattr(wrapper, "_run", fail)
    output = tmp_path / "run"
    assert wrapper.main(arguments(output)) == 2
    assert len(calls) == 1
    assert (output / "expected-code.json").exists()
    assert not (output / "completed.json").exists()
    assert not (output / "reports").exists()


@pytest.mark.parametrize("problem", ["existing_output", "inside_baseline", "bad_policy", "bad_top_k"])
def test_preflight_errors_prevent_generation(wrapper, tmp_path, monkeypatch, problem):
    output = tmp_path / "run"
    args = arguments(output)
    if problem == "existing_output":
        output.mkdir()
    elif problem == "inside_baseline":
        baseline_dir = tmp_path / "baseline"
        baseline_dir.mkdir()
        args[args.index("--baseline") + 1] = str(baseline_dir / "recording.json")
        args[-1] = str(baseline_dir / "nested-run")
    elif problem == "bad_policy":
        policy = tmp_path / "bad.json"
        policy.write_text("{} invalid")
        args[args.index("--policy") + 1] = str(policy)
    else:
        args[args.index("--top-k") + 1] = "0"

    def must_not_run(*args, **kwargs):
        pytest.fail("preflight error reached generation")

    monkeypatch.setattr(wrapper, "_run", must_not_run)
    assert wrapper.main(args) == 2
    assert not (output / "expected-code.json").exists()


@pytest.mark.parametrize("stage", ["code_drift", "input_drift", "comparison_error", "comparison_input_drift", "missing_reports"])
def test_stage_errors_do_not_mark_workflow_complete(wrapper, tmp_path, monkeypatch, stage):
    policy = tmp_path / "policy.json"
    policy.write_bytes((ROOT / "configs/gate.relative-only.v1.json").read_bytes())
    output = tmp_path / "run"
    args = arguments(output)
    args[args.index("--policy") + 1] = str(policy)
    calls = []

    def run_stage(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            if stage == "input_drift":
                policy.write_bytes(policy.read_bytes() + b"\n")
            return 0
        if stage == "comparison_input_drift":
            policy.write_bytes(policy.read_bytes() + b"\n")
        return 2 if stage == "comparison_error" else 0

    if stage == "code_drift":
        def drift(*args):
            raise ValueError("source drift")
        monkeypatch.setattr(wrapper, "verify_generation_sources", drift)
    monkeypatch.setattr(wrapper, "_run", run_stage)
    assert wrapper.main(args) == 2
    assert len(calls) == (1 if stage in ("code_drift", "input_drift") else 2)
    assert not (output / "completed.json").exists()
