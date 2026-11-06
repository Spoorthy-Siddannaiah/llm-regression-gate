import hashlib
import json
from pathlib import Path

import pytest

from llm_reliability.loading import load_dataset
from llm_reliability.models import Criticality
from llm_reliability.squad import prepare_squad, write_squad_subset


DIRECTORY = Path(__file__).resolve().parents[1] / "datasets/squad/v1"


def test_real_subset_loads_and_references_cover_all_cases():
    dataset = load_dataset(DIRECTORY / "dataset.json")
    sources = json.loads((DIRECTORY / "sources.json").read_text())
    references = json.loads((DIRECTORY / "references.json").read_text())
    assert len(dataset.cases) == 25
    assert len(sources) == 50
    assert set(references) == {case.case_id for case in dataset.cases}
    assert len({item["article_title"] for item in references.values()}) == 5
    for case in dataset.cases:
        reference = references[case.case_id]
        assert case.case_id == "squad-" + reference["upstream_question_id"]
        assert case.criticality == Criticality.STANDARD
        assert case.relevant_source_ids == [reference["source_id"]]
        assert case.required_facts == [reference["answers"][0]["text"]]
        context = sources[reference["source_id"]]
        for answer in reference["answers"]:
            start, text = answer["answer_start"], answer["text"]
            assert context[start:start + len(text)] == text


def test_committed_artifact_hashes_match_manifest():
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    assert manifest["license"] == "CC-BY-SA-4.0"
    assert manifest["baseline_status"] == "not_generated_no_model_execution"
    for name, expected in manifest["artifact_sha256"].items():
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == expected


def test_source_ids_are_exact_content_hashes():
    sources = json.loads((DIRECTORY / "sources.json").read_text())
    for source_id, context in sources.items():
        assert source_id == "squad-context-" + hashlib.sha256(context.encode("utf-8")).hexdigest()


def test_wrong_upstream_file_rejected_before_output(tmp_path):
    source = tmp_path / "wrong.json"
    source.write_bytes(b"{}")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="checksum mismatch"):
        write_squad_subset(source, output)
    assert not output.exists()


def test_missing_input_is_actionable(tmp_path):
    source = tmp_path / "missing.json"
    with pytest.raises(ValueError) as caught:
        write_squad_subset(source, tmp_path / "output")
    assert str(source) in str(caught.value)


def test_arbitrary_or_malformed_bytes_are_not_accepted():
    with pytest.raises(ValueError, match="checksum mismatch"):
        prepare_squad(b"not the pinned official file")
