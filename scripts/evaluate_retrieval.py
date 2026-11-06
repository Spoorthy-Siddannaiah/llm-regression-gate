"""Measure local retrieval on a versioned dataset; does not generate answers."""

import argparse
import hashlib
import json
from pathlib import Path

from llm_reliability.loading import load_corpus, load_dataset
from llm_reliability.models import RecordedResponse
from llm_reliability.retrieval import BM25Retriever
from llm_reliability.source_checks import check_retrieval_recall


def evaluate(dataset_path: Path, sources_path: Path) -> dict:
    dataset = load_dataset(dataset_path)
    retriever = BM25Retriever(load_corpus(sources_path))
    cutoffs = (1, 3, 5)
    cases = []
    for case in dataset.cases:
        hits = retriever.retrieve(case.question, top_k=max(cutoffs))
        # Only adapt retrieval IDs to the existing metric interface. These empty
        # fields are not generated answers/citations and are not saved as recordings.
        observation = RecordedResponse(
            case_id=case.case_id, answer="", cited_source_ids=[],
            retrieved_source_ids=[hit.source_id for hit in hits],
        )
        cases.append({
            "case_id": case.case_id,
            "ranked_hits": [{"source_id": hit.source_id, "score": hit.score} for hit in hits],
            "recall": {
                str(k): check_retrieval_recall(case, observation, k=k).recall_at_k
                for k in cutoffs
            },
        })
    return {
        "artifact_kind": "retrieval_only_measurement", "schema_version": 1,
        "dataset_id": dataset.dataset_id, "dataset_version": dataset.dataset_version,
        "input_sha256": {
            "dataset": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "sources": hashlib.sha256(sources_path.read_bytes()).hexdigest(),
        },
        "settings": retriever.settings.model_dump(mode="json"),
        "cutoffs": cutoffs, "case_count": len(cases),
        "mean_recall": {
            str(k): sum(case["recall"][str(k)] for case in cases) / len(cases)
            for k in cutoffs
        },
        "cases": cases,
        "limits": "Small selected corpus; associated-context labels; no answer generation, latency benchmark, or accepted model baseline.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(args.dataset, args.sources)
        content = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except (OSError, ValueError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(json.dumps(report["mean_recall"], sort_keys=True))


if __name__ == "__main__":
    main()
