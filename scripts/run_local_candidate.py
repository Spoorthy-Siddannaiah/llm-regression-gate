"""Opt-in local generation followed by strict comparison; never promotes a baseline."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pydantic import TypeAdapter

from llm_reliability.loading import load_comparison, load_evaluation_settings, load_gate_policy
from llm_reliability.models import Identifier
from llm_reliability.run_provenance import capture_code_provenance, verify_generation_sources


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


def _run(command: list[str], *, cwd: Path, timeout: int) -> int:
    return subprocess.run(command, cwd=cwd, timeout=timeout).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog="Exit 0=pass, 1=quality failure, 2=execution/input error.")
    for name in ("dataset", "sources", "baseline", "policy", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--recording-id", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        paths = {name: getattr(args, name).resolve() for name in ("dataset", "sources", "baseline", "policy")}
        paths["baseline_manifest"] = paths["baseline"].parent / "manifest.json"
        if args.settings is not None:
            paths["settings"] = args.settings.resolve()
        output = args.output_dir.resolve()
        if output.exists():
            raise ValueError(f"output directory already exists: {output}")
        if output.is_relative_to(paths["baseline"].parent):
            raise ValueError("output directory must not be inside the baseline run")
        if args.top_k <= 0:
            raise ValueError("top-k must be a positive integer")
        recording_id = TypeAdapter(Identifier, config={"strict": True}).validate_python(args.recording_id)
        # Reject bad data, baseline provenance, or policy before any generation call.
        reference = load_comparison(paths["dataset"], paths["baseline"], paths["baseline"],
                                    sources_path=paths["sources"], require_manifests=True)
        load_gate_policy(paths["policy"])
        if "settings" in paths:
            load_evaluation_settings(paths["settings"])
        inputs_before = _hashes(paths)
        expected = capture_code_provenance(root)
        if expected.git_status != "available":
            raise ValueError("Git revision unavailable; cannot create a strict candidate target")
        output.mkdir(parents=True, exist_ok=False)
        expected_path = output / "expected-code.json"
        _write_json(expected_path, expected.model_dump(mode="json"))
        _write_json(output / "started.json", {
            "status": "incomplete_until_completed_json", "started_at": datetime.now(timezone.utc).isoformat(),
            "input_sha256": inputs_before, "recording_id": recording_id, "retrieval_top_k": args.top_k,
        })
        candidate = output / "candidate"
        status = _run([
            sys.executable, str(root / "scripts/record_ollama.py"),
            "--dataset", str(paths["dataset"]), "--sources", str(paths["sources"]),
            "--recording-id", recording_id, "--output-dir", str(candidate), "--top-k", str(args.top_k),
        ], cwd=root, timeout=3600)
        if status != 0:
            raise ValueError(f"local generation failed (exit {status}); comparison was not run")
        verify_generation_sources(expected, root)
        if _hashes(paths) != inputs_before:
            raise ValueError("dataset/corpus/baseline/policy/settings changed during generation; comparison was not run")
        comparison = [
            sys.executable, "-m", "llm_reliability", "--dataset", str(paths["dataset"]),
            "--sources", str(paths["sources"]), "--require-manifests",
            "--baseline", str(paths["baseline"]), "--candidate", str(candidate / "recording.json"),
            "--policy", str(paths["policy"]), "--expected-candidate-code", str(expected_path),
            "--output-dir", str(output / "reports"),
        ]
        if "settings" in paths:
            comparison.extend(["--settings", str(paths["settings"])])
        status = _run(comparison, cwd=root, timeout=120)
        if status not in (0, 1):
            raise ValueError(f"strict comparison failed to execute (exit {status})")
        verify_generation_sources(expected, root)
        if _hashes(paths) != inputs_before:
            raise ValueError("inputs changed during comparison; workflow not completed")
        report_path = output / "reports/report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        try:
            identity = (
                report["evaluation"]["dataset_id"], report["evaluation"]["dataset_version"],
                report["evaluation"]["baseline"]["recording_id"], report["evaluation"]["candidate"]["recording_id"],
            )
            if report["passed"] is not (status == 0) or identity != (
                reference.dataset.dataset_id, reference.dataset.dataset_version,
                reference.baseline.recording_id, recording_id,
            ):
                raise ValueError("comparison report outcome/identity does not match requested run")
        except (KeyError, TypeError) as error:
            raise ValueError("comparison report has invalid outcome/identity fields") from error
        report_hashes = _hashes({
            "report.json": report_path, "report.md": output / "reports/report.md",
        })
        _write_json(output / "completed.json", {
            "status": "gate_passed" if status == 0 else "gate_failed", "exit_code": status,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "baseline_promoted": False,
            "report_sha256": report_hashes,
        })
        print(f"Local candidate workflow complete: exit {status}; {output}", flush=True)
        return status
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}. Inspect partial output; retry in a new directory.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
