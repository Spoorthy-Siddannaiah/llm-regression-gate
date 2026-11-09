import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "recordings/squad/llama3.2-bm25-v1"
CANDIDATE = ROOT / "recordings/squad/llama3.2-bm25-top1-v1"


def test_experiment_changes_only_passage_budget_and_preserves_baseline():
    artifact = json.loads((ROOT / "benchmarks/squad-top1-experiment-v1.json").read_text())
    baseline = json.loads((BASELINE / "manifest.json").read_text())
    candidate = json.loads((CANDIDATE / "manifest.json").read_text())
    assert (baseline["retrieval_top_k"], candidate["retrieval_top_k"]) == (3, 1)
    assert baseline["model"]["digest"] == candidate["model"]["digest"]
    for field in artifact["verified_equal_manifest_fields"]:
        if field != "model.digest":
            assert baseline[field] == candidate[field]
    for name, digest in artifact["baseline_file_sha256"].items():
        assert hashlib.sha256((BASELINE / name).read_bytes()).hexdigest() == digest
    for side, directory in (("baseline", BASELINE), ("candidate", CANDIDATE)):
        assert artifact["recording_sha256"][side] == hashlib.sha256(
            (directory / "recording.json").read_bytes()
        ).hexdigest()
    for index in range(1, 26):
        old = json.loads((BASELINE / f"evidence/{index:03d}.request.json").read_text())["request"]
        new = json.loads((CANDIDATE / f"evidence/{index:03d}.request.json").read_text())["request"]
        old_user = json.loads(old["messages"][1]["content"])
        new_user = json.loads(new["messages"][1]["content"])
        assert new_user["question"] == old_user["question"]
        assert new_user["sources"] == old_user["sources"][:1]
        assert new["messages"][0] == old["messages"][0]
        for field in ("model", "options", "format", "stream", "keep_alive"):
            assert new[field] == old[field]


def test_real_candidate_cli_replay_detects_relative_regressions(tmp_path):
    output = tmp_path / "reports"
    command = [
        sys.executable, "-m", "llm_reliability",
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--baseline", str(BASELINE / "recording.json"),
        "--candidate", str(CANDIDATE / "recording.json"),
        "--policy", str(ROOT / "configs/gate.relative-only.v1.json"),
        "--settings", str(ROOT / "configs/evaluator.v1.json"),
        "--output-dir", str(output),
    ]
    process = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 1, process.stderr
    report = json.loads((output / "report.json").read_text())
    artifact = json.loads((ROOT / "benchmarks/squad-top1-experiment-v1.json").read_text())
    assert report.pop("provenance")
    assert report.pop("case_changes")
    report["report_schema_version"] = artifact["comparison"]["report_schema_version"]
    assert report == artifact["comparison"]
    assert {failure["code"] for failure in report["failures"]} == {"excessive_drop"}
    assert {failure["metric"] for failure in report["failures"]} == {
        "fact_coverage", "citation_label_coverage", "retrieval_recall",
    }
    assert all(value["minimum"] == 0.0 for value in (
        report["policy"]["fact_coverage"], report["policy"]["citation_label_coverage"],
        report["policy"]["retrieval_recall"],
    ))


def test_actual_citation_enum_candidate_passes_without_losing_other_metrics(tmp_path):
    candidate = ROOT / "recordings/squad/llama3.2-bm25-citation-enum-v2"
    old = json.loads((BASELINE / "recording.json").read_text())
    new = json.loads((candidate / "recording.json").read_text())
    changed = [a["case_id"] for a, b in zip(old["responses"], new["responses"], strict=True) if a != b]
    assert changed == ["squad-56e17644e3433e1400422f40"]
    for index in range(1, 26):
        before = json.loads((BASELINE / f"evidence/{index:03d}.request.json").read_text())["request"]
        after = json.loads((candidate / f"evidence/{index:03d}.request.json").read_text())["request"]
        sources = json.loads(after["messages"][1]["content"])["sources"]
        choices = after["format"]["properties"]["cited_source_ids"]["items"].pop("enum")
        assert choices == [source["source_id"] for source in sources]
        assert before == after  # The only request change was the citation enum.
    output = tmp_path / "reports"
    process = subprocess.run([
        sys.executable, "-m", "llm_reliability",
        "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"), "--require-manifests",
        "--baseline", str(BASELINE / "recording.json"),
        "--candidate", str(candidate / "recording.json"),
        "--expected-candidate-code", str(candidate / "expected-code.json"),
        "--policy", str(ROOT / "configs/gate.citation-v2.json"),
        "--settings", str(ROOT / "configs/evaluator.v1.json"),
        "--output-dir", str(output),
    ], cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    report = json.loads((output / "report.json").read_text())
    assert report["passed"] is True and report["failures"] == []
    assert all(metric["delta"] == 0 for metric in report["metrics"])
    assert report["citation_existence_gate"]["baseline_unknown_count"] == 1
    assert report["citation_existence_gate"]["candidate_unknown_count"] == 0
    assert report["citation_existence_gate"]["increase"] == -1
