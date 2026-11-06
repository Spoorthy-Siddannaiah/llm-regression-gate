"""Import a fixed real SQuAD slice; no network access or generated model answers."""

import hashlib
import json
from pathlib import Path

from llm_reliability.models import Criticality, Dataset, EvaluationCase


REVISION = "240e165ab706d95bd4323653bb92421f446208cf"
UPSTREAM_SHA256 = "95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9"
UPSTREAM_URL = (
    f"https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/{REVISION}"
    "/dataset/dev-v1.1.json"
)


def prepare_squad(raw: bytes) -> dict[str, bytes]:
    """Return reproducible artifact bytes for the exact pinned development file.

    Select first five articles, first ten paragraphs/article as corpus, and the
    first question in each of the first five paragraphs/article as evaluation.
    The first human answer span is a narrow required-phrase proxy, not a general
    semantic assertion. All answer alternatives remain in references.json.
    """
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_SHA256:
        raise ValueError(f"SQuAD input checksum mismatch; expected SHA-256 {UPSTREAM_SHA256}")
    upstream = json.loads(raw)
    cases = []
    sources = {}
    references = {}
    selections = []
    for article_index, article in enumerate(upstream["data"][:5]):
        for paragraph_index, paragraph in enumerate(article["paragraphs"][:10]):
            context = paragraph["context"]
            source_id = "squad-context-" + hashlib.sha256(context.encode("utf-8")).hexdigest()
            sources[source_id] = context
            if paragraph_index >= 5:
                continue
            qa = paragraph["qas"][0]
            for answer in qa["answers"]:
                start, text = answer["answer_start"], answer["text"]
                if context[start:start + len(text)] != text:
                    raise ValueError(f"SQuAD case {qa['id']}: annotated answer does not match context")
            case_id = "squad-" + qa["id"]
            cases.append(EvaluationCase(
                case_id=case_id, question=qa["question"],
                required_facts=[qa["answers"][0]["text"]],
                relevant_source_ids=[source_id], criticality=Criticality.STANDARD,
            ))
            references[case_id] = {
                "upstream_question_id": qa["id"], "article_title": article["title"],
                "answers": qa["answers"], "source_id": source_id,
            }
            selections.append({
                "case_id": case_id, "source_id": source_id,
                "article_index": article_index, "paragraph_index": paragraph_index,
                "question_index": 0,
            })
    dataset = Dataset(
        dataset_id="squad-v1.1-dev-slice", dataset_version="1.0.0", cases=cases,
    )

    def encode(value: object) -> bytes:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")

    artifacts = {
        "dataset.json": encode(dataset.model_dump(mode="json")),
        "sources.json": encode(sources),
        "references.json": encode(references),
    }
    manifest = {
        "manifest_version": 1, "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version, "upstream_url": UPSTREAM_URL,
        "upstream_revision": REVISION, "upstream_sha256": UPSTREAM_SHA256,
        "upstream_split": "development", "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "SQuAD: Rajpurkar, Zhang, Lopyrev and Liang (2016); contexts derived from Wikipedia.",
        "citation_url": "https://aclanthology.org/D16-1264/",
        "source_homepage": "https://rajpurkar.github.io/SQuAD-explorer/",
        "changes": "Selected 25 original questions and 50 contexts; assigned content-hash source IDs; first annotated answer used as required phrase; all cases standard.",
        "selection": "First 5 articles, first 10 paragraphs each; first question of paragraphs 0..4 each.",
        "case_count": len(cases), "source_count": len(sources),
        "labels": "Associated original context; not exhaustive corpus-wide relevance judgments.",
        "fact_policy": "First annotated span only; alternatives preserved separately, not accepted by current phrase scorer.",
        "criticality_policy": "All standard; no domain-critical labels have been reviewed.",
        "baseline_status": "not_generated_no_model_execution",
        "selections": selections,
        "artifact_sha256": {
            name: hashlib.sha256(content).hexdigest() for name, content in artifacts.items()
        },
    }
    artifacts["manifest.json"] = encode(manifest)
    return artifacts


def write_squad_subset(input_path: str | Path, output_directory: str | Path) -> None:
    """Write only into a new directory; a write failure may leave partial output."""
    source, output = Path(input_path), Path(output_directory)
    try:
        artifacts = prepare_squad(source.read_bytes())
        output.mkdir(parents=True, exist_ok=False)
        for name, content in artifacts.items():
            with (output / name).open("xb") as stream:
                stream.write(content)
    except (OSError, ValueError) as error:
        raise ValueError(
            f"SQuAD preparation failed (input={source}, output={output}): {error}. "
            "Existing output is never replaced; inspect for partial artifacts."
        ) from error
