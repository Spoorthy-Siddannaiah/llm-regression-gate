"""Capture an explicit expected-code snapshot without generation or baseline changes."""

import argparse
from pathlib import Path

from llm_reliability.run_provenance import capture_code_provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        snapshot = capture_code_provenance(args.project_root)
        if snapshot.git_status != "available":
            raise ValueError("Git revision unavailable; cannot create a freshness target")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(snapshot.model_dump_json(indent=2) + "\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(f"Captured expected code snapshot: {args.output}")


if __name__ == "__main__":
    main()
