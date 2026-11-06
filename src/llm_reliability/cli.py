"""One offline comparison command with explicit process outcomes."""

import argparse
from pathlib import Path
import sys

from llm_reliability.gates import compare_and_gate
from llm_reliability.loading import (
    InputLoadError, load_comparison, load_evaluation_settings, load_gate_policy,
)
from llm_reliability.reports import ReportWriteError, write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare local recorded responses; no live model calls.",
        epilog="Exit codes: 0=gate passed, 1=gate failed, 2=input/execution error.",
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path, help="New report directory")
    parser.add_argument("--policy", type=Path, help="Optional GatePolicy JSON file")
    parser.add_argument("--settings", type=Path, help="Optional EvaluationSettings JSON file")
    args = parser.parse_args(argv)
    try:
        inputs = load_comparison(args.dataset, args.baseline, args.candidate)
        policy = load_gate_policy(args.policy) if args.policy else None
        settings = load_evaluation_settings(args.settings) if args.settings else None
        result = compare_and_gate(inputs, policy=policy, settings=settings)
        json_path, markdown_path = write_reports(result, args.output_dir)
        print(f"{'PASS' if result.passed else 'FAIL'}: {len(result.failures)} gate failure(s)")
        for failure in result.failures:
            print(f"- {failure.code}: {failure.message}")
        print(f"JSON: {json_path}")
        print(f"Markdown: {markdown_path}")
        return 0 if result.passed else 1
    except (InputLoadError, ReportWriteError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        # Unexpected evaluator bugs must never look like a quality regression.
        # Avoid dumping potentially sensitive payloads in an exception message.
        print(
            f"ERROR: unexpected {type(error).__name__}; evaluation did not complete. "
            "Inspect the output directory for partial artifacts.", file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
