"""Offline diagnostic on real reference variants; no gate decisions or model calls."""

import argparse
import json
from pathlib import Path

from llm_reliability.alternative_diagnostics import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "sources", "references", "baseline", "candidate", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.dataset, args.sources, args.references, args.baseline, args.candidate)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    for role, summary in result["results"].items():
        print(f"{role}: v1={summary['required_fact_case_coverage_v1']:.2f}, alternatives={summary['alternative_case_coverage']:.2f}")


if __name__ == "__main__":
    main()
