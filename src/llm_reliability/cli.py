"""One offline comparison command with explicit process outcomes."""

import argparse
import hashlib
from pathlib import Path
import sys

from llm_reliability.gates import compare_and_gate
from llm_reliability.loading import (
    InputLoadError, load_comparison, load_corpus, load_evaluation_settings, load_gate_policy,
)
from llm_reliability.reports import ReportWriteError, write_reports
from llm_reliability.alternative_diagnostics import build_diagnostic
from llm_reliability.citation_existence import build_citation_existence


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
    parser.add_argument("--sources", type=Path, help="Corpus for manifest validation; defaults to sources.json beside dataset")
    parser.add_argument("--require-manifests", action="store_true", help="Require completed manifests for both recordings")
    parser.add_argument("--answer-alternatives", type=Path, help="Optional SQuAD reference JSON for report-only alternative-answer evidence")
    parser.add_argument("--citation-existence", action="store_true", help="Report cited-ID membership in the supplied corpus; does not affect the gate")
    args = parser.parse_args(argv)
    try:
        inputs = load_comparison(
            args.dataset, args.baseline, args.candidate,
            sources_path=args.sources, require_manifests=args.require_manifests,
        )
        policy = load_gate_policy(args.policy) if args.policy else None
        settings = load_evaluation_settings(args.settings) if args.settings else None
        diagnostic = None
        if args.answer_alternatives is not None:
            try:
                diagnostic = build_diagnostic(
                    args.dataset, args.sources or args.dataset.with_name("sources.json"),
                    args.answer_alternatives, args.baseline, args.candidate,
                )
            except (OSError, ValueError) as error:
                raise InputLoadError(f"answer alternatives ({args.answer_alternatives}): {error}") from error
        citation_diagnostic = None
        if args.citation_existence:
            sources = args.sources or args.dataset.with_name("sources.json")
            try:
                citation_diagnostic = build_citation_existence(
                    inputs, load_corpus(sources),
                    corpus_sha256=hashlib.sha256(sources.read_bytes()).hexdigest(),
                )
            except (OSError, ValueError) as error:
                raise InputLoadError(f"citation existence ({sources}): {error}") from error
        result = compare_and_gate(inputs, policy=policy, settings=settings)
        json_path, markdown_path = write_reports(
            result, args.output_dir, answer_alternatives=diagnostic,
            citation_existence=citation_diagnostic,
        )
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
