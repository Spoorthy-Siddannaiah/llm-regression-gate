"""Explicit opt-in local generation; writes a new recording, never promotes a baseline."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

from pydantic import ValidationError

from llm_reliability.generation import (
    LocalOllama, MODEL, MODEL_DIGEST, OPTIONS, PROMPT_VERSION, SYSTEM_PROMPT,
    build_request, parse_answer,
)
from llm_reliability.loading import parse_input_bytes, validate_source_references
from llm_reliability.models import Configuration, Dataset, RecordedResponse, Recording
from llm_reliability.retrieval import BM25Retriever, SourceCorpus
from llm_reliability.run_provenance import capture_code_provenance, verify_generation_sources


def write_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def safe_error_details(error: Exception) -> str:
    """Only fixed categories and known schema locations may enter console logs."""
    if isinstance(error, ValidationError):
        allowed = {"answer", "cited_source_ids", "done", "done_reason", "message", "content", "role"}
        details = []
        for item in error.errors(include_input=False, include_url=False)[:10]:
            location = ".".join(str(p) if isinstance(p, int) or p in allowed else "<field>" for p in item["loc"])
            details.append(f"{item['type']}@{location or '<root>'}")
        return "validation_error " + "; ".join(details)
    if isinstance(error, OSError):
        return "io_or_transport_error"
    if isinstance(error, ValueError):
        return "invalid_input_or_response"
    return "unexpected_error"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--recording-id", required=True)
    parser.add_argument("--top-k", type=int, default=3, help="Number of BM25 passages sent to the model")
    parser.add_argument("--limit", type=int, help="Smoke test only; not a full comparison recording")
    args = parser.parse_args()
    stage = "input_snapshot"
    try:
        paths = {"dataset": args.dataset, "sources": args.sources}
        snapshots = {name: path.read_bytes() for name, path in paths.items()}
        input_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in snapshots.items()}
        dataset = parse_input_bytes(snapshots["dataset"], Dataset, source=args.dataset)
        corpus = parse_input_bytes(snapshots["sources"], SourceCorpus, source=args.sources)
        validate_source_references(dataset, corpus)
        retriever = BM25Retriever(corpus)
        if args.limit is not None and not 1 <= args.limit <= len(dataset.cases):
            raise ValueError("limit must be between 1 and dataset case count")
        if args.top_k <= 0:
            raise ValueError("top-k must be a positive integer")
        project_root = Path(__file__).resolve().parents[1]
        code_provenance = capture_code_provenance(project_root)
        stage = "provider_metadata"
        client = LocalOllama()
        model = client.verify_model()
        server = client.request("/api/version")
        model_metadata = client.request("/api/show", {"model": MODEL})
        # Keep reproducibility fields without embedding a user's local model path
        # or unnecessary tensor listings in a portable recording artifact.
        model_metadata = {key: value for key, value in model_metadata.items()
                          if key not in ("modelfile", "tensors")}
        args.output_dir.mkdir(parents=True, exist_ok=False)
        evidence = args.output_dir / "evidence"
        evidence.mkdir()
        write_json(args.output_dir / "code-provenance.json", code_provenance.model_dump(mode="json"))
        started = datetime.now(timezone.utc).isoformat()
        write_json(args.output_dir / "started.json", {
            "started_at": started, "status": "incomplete_until_manifest_written",
            "requested_recording_id": args.recording_id,
        })
        observations = []
        cases = dataset.cases[:args.limit] if args.limit is not None else dataset.cases
        for number, case in enumerate(cases, 1):
            stage = f"generation_case_{number}"
            hits = retriever.retrieve(case.question, top_k=args.top_k)
            payload = build_request(case.question, hits)
            # Numbered paths avoid interpreting upstream IDs as filesystem paths.
            prefix = evidence / f"{number:03d}"
            write_json(prefix.with_suffix(".request.json"), {"case_id": case.case_id, "request": payload})
            raw = client.request("/api/chat", payload)
            write_json(prefix.with_suffix(".response.json"), {"case_id": case.case_id, "response": raw})
            answer = parse_answer(raw)
            observations.append(RecordedResponse(
                case_id=case.case_id, answer=answer.answer,
                cited_source_ids=answer.cited_source_ids,
                retrieved_source_ids=[hit.source_id for hit in hits],
            ))
            print(f"[{number}/{len(cases)}] recorded", flush=True)
        stage = "completion_validation"
        client.verify_model()  # Reject a tag changed during this run.
        verify_generation_sources(code_provenance, project_root)
        if any(path.read_bytes() != snapshots[name] for name, path in paths.items()):
            stage = "input_drift"
            raise ValueError("input drift")
        recording = Recording(
            recording_id=args.recording_id, dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            configuration=Configuration(
                configuration_id="ollama-llama3.2-bm25",
                configuration_version="1.1.0" if args.top_k == 3 else f"1.1.0-top{args.top_k}",
                model_version=f"{MODEL}@sha256:{MODEL_DIGEST}",
                prompt_version=PROMPT_VERSION, retrieval_version=f"bm25-v1-top{args.top_k}",
            ), responses=observations,
        )
        write_json(args.output_dir / "recording.json", recording.model_dump(mode="json"))
        if any(path.read_bytes() != snapshots[name] for name, path in paths.items()):
            stage = "input_drift"
            raise ValueError("input drift")
        write_json(args.output_dir / "manifest.json", {
            "manifest_version": 1, "status": "completed_not_promoted",
            "code_provenance": code_provenance.model_dump(mode="json"),
            "scope": "smoke_subset" if args.limit is not None else "full_dataset",
            "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
            "recording_id": recording.recording_id, "case_count": len(observations),
            "model": model, "server": server, "model_metadata": model_metadata,
            "metadata_omissions": ["modelfile (local filesystem paths)", "tensors"],
            "generation_options": OPTIONS, "system_prompt": SYSTEM_PROMPT,
            "prompt_version": PROMPT_VERSION, "retrieval_top_k": args.top_k,
            "retrieval_settings": retriever.settings.model_dump(mode="json"),
            "platform": platform.platform(), "python": platform.python_version(),
            "input_sha256": input_hashes,
            "artifact_sha256": {
                str(path.relative_to(args.output_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(args.output_dir.rglob("*.json"))
            },
            "limits": "Temperature/seed do not guarantee cross-runtime determinism. No semantic correctness judgment or automatic baseline acceptance.",
        })
        print(f"Completed recording, not promoted: {args.output_dir}", flush=True)
    except Exception as error:
        parser.exit(2, f"ERROR: recording_failed stage={stage} {safe_error_details(error)}. "
                    "Inspect restricted raw evidence; retry in a new directory.\n")


if __name__ == "__main__":
    main()
