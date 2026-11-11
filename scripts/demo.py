"""Explain the recorded experiments after verifying all eight offline replay scenarios."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "fact_coverage": "Required-phrase coverage",
    "citation_label_coverage": "Citation-label coverage",
    "retrieval_recall": "Retrieval Recall@3",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="New report directory; defaults to a temporary location")
    args = parser.parse_args(argv)
    try:
        output = (args.output_dir.resolve() if args.output_dir is not None else
                  Path(tempfile.mkdtemp(prefix="llm-regression-demo-")) / "reports")
        # Reuse the existing verifier's exits, failure-reason checks and baseline hashes.
        # This wrapper displays evidence; it does not calculate scores or select policies.
        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_replays.py"), "--output-dir", str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
        if process.returncode != 0:
            print("ERROR: offline replay verification failed; demo not verified.", file=sys.stderr)
            print(process.stderr.strip() or process.stdout.strip(), file=sys.stderr)
            return 2
        regression = json.loads((output / "squad-regression/report.json").read_text())
        fix = json.loads((output / "citation-enum/report.json").read_text())
        case_id = "squad-56be4eafacb8001400a50302"
        dataset = json.loads((ROOT / "datasets/squad/v1/dataset.json").read_text())
        question = next(case["question"] for case in dataset["cases"] if case["case_id"] == case_id)
        answers = []
        for name in ("llama3.2-bm25-v1", "llama3.2-bm25-top1-v1"):
            recording = json.loads((ROOT / f"recordings/squad/{name}/recording.json").read_text())
            answers.append(next(item["answer"] for item in recording["responses"] if item["case_id"] == case_id))

        print("LLM Regression Gate: offline recorded-response demonstration")
        print(f"Dataset: {len(dataset['cases'])} SQuAD questions; no fresh model inference\n")
        print("1. Retrieval change: three passages -> one passage")
        print(f"Gate: {'PASS' if regression['passed'] else 'FAIL'} (expected exit 1)")
        for metric in regression["metrics"]:
            print(f"  {LABELS[metric['metric']]}: {metric['baseline']:.1%} -> {metric['candidate']:.1%} "
                  f"({metric['delta'] * 100:+.1f} percentage points)")
        print(f"  Question: {question}")
        print(f"  Baseline answer: {answers[0]!r}; candidate answer: {answers[1]!r}\n")
        print("2. Citation-schema change: constrain choices to retrieved source IDs")
        print(f"Gate: {'PASS' if fix['passed'] else 'FAIL'} (expected exit 0)")
        evidence = fix["citation_existence_gate"]
        print(f"  Unknown citation occurrences: {evidence['baseline_unknown_count']} -> {evidence['candidate_unknown_count']}")
        print(f"  Coverage/recall deltas: {', '.join(format(m['delta'], '+.2f') for m in fix['metrics'])}")
        print(f"  Policy: {fix['policy']['policy_version']} (unchanged)\n")
        print("DEMO VERIFIED: all eight scenarios returned their expected exits and reasons.")
        print("All 54 fixed-baseline hashes match; the baseline was not promoted.")
        print("Demo exit 0 means expected outcomes were verified, including rejection of bad candidates.")
        print("Limits: small selected dataset; phrase/ID checks do not prove semantic correctness.")
        print("The baseline has known defects and is an observed reference, not an approved model.")
        print(f"Reports (eight JSON + eight Markdown): {output}")
        return 0
    except (OSError, ValueError, KeyError, StopIteration, TypeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {type(error).__name__}; demo did not complete. Inspect the report directory.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
