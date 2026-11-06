"""Offline preparation after downloading the pinned source; see dataset README."""

import argparse

from llm_reliability.squad import write_squad_subset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        write_squad_subset(args.input, args.output_dir)
    except ValueError as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(f"Prepared real SQuAD subset: {args.output_dir}")


if __name__ == "__main__":
    main()
