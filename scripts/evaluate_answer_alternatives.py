"""Offline diagnostic on real reference variants; no gate decisions or model calls."""

import argparse
import hashlib
import json
from pathlib import Path

from pydantic import Field, RootModel

from llm_reliability.answer_alternatives import check_answer_alternatives, from_reference_answers
from llm_reliability.fact_checks import check_required_facts
from llm_reliability.loading import load_comparison, load_corpus
from llm_reliability.models import Contract, Identifier


class ReferenceAnswer(Contract):
    answer_start: int = Field(ge=0)
    text: Identifier


class Reference(Contract):
    upstream_question_id: Identifier
    article_title: Identifier
    source_id: Identifier
    answers: list[ReferenceAnswer] = Field(min_length=1)


class References(RootModel[dict[str, Reference]]):
    pass


def evaluate(dataset: Path, sources: Path, references: Path, baseline: Path, candidate: Path) -> dict:
    inputs = load_comparison(dataset, baseline, candidate, sources_path=sources, require_manifests=True)
    annotations = References.model_validate_json(references.read_text(encoding="utf-8")).root
    corpus = load_corpus(sources).root
    expected_ids = {case.case_id for case in inputs.dataset.cases}
    if set(annotations) != expected_ids:
        raise ValueError(f"reference case coverage mismatch: missing={sorted(expected_ids - annotations.keys())}, unexpected={sorted(annotations.keys() - expected_ids)}")
    results = {}
    for role, recording in (("baseline", inputs.baseline), ("candidate", inputs.candidate)):
        responses = {response.case_id: response for response in recording.responses}
        cases = []
        for case in inputs.dataset.cases:
            reference = annotations[case.case_id]
            if reference.source_id not in case.relevant_source_ids:
                raise ValueError(f"{case.case_id}: reference source does not match dataset labels")
            if reference.source_id not in corpus:
                raise ValueError(f"{case.case_id}: reference source absent from corpus")
            context = corpus[reference.source_id]
            for answer in reference.answers:
                if context[answer.answer_start:answer.answer_start + len(answer.text)] != answer.text:
                    raise ValueError(f"{case.case_id}: reference answer span does not match source")
            expectation = from_reference_answers(case.case_id, [answer.text for answer in reference.answers])
            observation = responses[case.case_id]
            variant_result = check_answer_alternatives(expectation, observation)
            cases.append({
                "case_id": case.case_id, "alternatives": expectation.alternatives,
                "required_facts_present_v1": check_required_facts(case, observation).all_required_facts_present,
                "alternative_result": variant_result.model_dump(mode="json"),
            })
        results[role] = {
            "recording_id": recording.recording_id,
            "required_fact_case_coverage_v1": sum(c["required_facts_present_v1"] for c in cases) / len(cases),
            "alternative_case_coverage": sum(c["alternative_result"]["any_alternative_present"] for c in cases) / len(cases),
            "cases": cases,
        }
    return {
        "artifact_kind": "alternative_answer_diagnostic", "schema_version": 1,
        "evaluator_version": "alternative-phrases-v1", "case_count": len(expected_ids),
        "input_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in (("dataset", dataset), ("sources", sources), ("references", references),
                               ("baseline", baseline), ("candidate", candidate))
        },
        "results": results,
        "limits": "OR of literal annotated phrases only, not semantic correctness. No invented aliases, unit conversion, negation handling, gate changes, or baseline promotion.",
    }


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
