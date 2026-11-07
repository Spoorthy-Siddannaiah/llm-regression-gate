import json
from pathlib import Path
import subprocess
import sys
import hashlib

import pytest

from llm_reliability.citation_existence import build_citation_existence, check_citation_existence
from llm_reliability.gates import compare_and_gate
from llm_reliability.loading import load_comparison, load_corpus
from llm_reliability.reports import render_markdown, write_reports
from llm_reliability.models import Criticality, EvaluationCase, RecordedResponse
from llm_reliability.retrieval import SourceCorpus
from llm_reliability.source_checks import check_citation_ids


def response(citations):
    return RecordedResponse(case_id="example", answer="", cited_source_ids=citations, retrieved_source_ids=[])


@pytest.mark.parametrize("cited, existing, unknown, status", [
    (["a"], ("a",), (), True),
    (["external"], (), ("external",), False),
    (["external", "b", "a"], ("b", "a"), ("external",), False),
    ([], (), (), None),
    (["A"], (), ("A",), False),
])
def test_exact_membership_preserves_ids_and_handles_missing_citations(cited, existing, unknown, status):
    corpus = SourceCorpus({"a": "First passage", "b": "Second passage"})
    observation = response(cited)
    before = observation.model_dump_json(), corpus.model_dump_json()
    result = check_citation_existence(observation, corpus)
    assert result.existing_source_ids == existing
    assert result.unknown_source_ids == unknown
    assert result.all_cited_ids_exist is status
    assert result.has_citations == bool(cited)
    assert before == (observation.model_dump_json(), corpus.model_dump_json())


def test_unlabelled_source_can_exist_even_when_not_retrieved():
    corpus = SourceCorpus({"a": "Labelled passage", "b": "Other passage"})
    case = EvaluationCase(
        case_id="example", question="Question?", required_facts=["fact"],
        relevant_source_ids=["a"], criticality=Criticality.STANDARD,
    )
    observation = response(["b"])
    assert check_citation_ids(case, observation).unlabelled_cited_source_ids == ("b",)
    assert check_citation_existence(observation, corpus).unknown_source_ids == ()
    assert check_citation_existence(observation, corpus).all_cited_ids_exist is True


ROOT = Path(__file__).resolve().parents[1]


def command(output, candidate):
    return [
        sys.executable, "-m", "llm_reliability", "--dataset", str(ROOT / "datasets/squad/v1/dataset.json"),
        "--sources", str(ROOT / "datasets/squad/v1/sources.json"), "--require-manifests",
        "--baseline", str(ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json"),
        "--candidate", str(ROOT / "recordings/squad" / candidate / "recording.json"),
        "--output-dir", str(output),
    ]


@pytest.mark.parametrize("candidate, expected", [("llama3.2-bm25-v1", 0), ("llama3.2-bm25-top1-v1", 1)])
@pytest.mark.parametrize("with_alternatives", [False, True])
def test_real_cli_diagnostics_preserve_gate_and_work_together(tmp_path, candidate, expected, with_alternatives):
    plain, extended = tmp_path / "plain", tmp_path / "extended"
    first = subprocess.run(command(plain, candidate), capture_output=True, text=True)
    flags = ["--citation-existence"]
    if with_alternatives:
        flags += ["--answer-alternatives", str(ROOT / "datasets/squad/v1/references.json")]
    second = subprocess.run([*command(extended, candidate), *flags], capture_output=True, text=True)
    assert first.returncode == second.returncode == expected, second.stderr
    original = json.loads((plain / "report.json").read_text())
    report = json.loads((extended / "report.json").read_text())
    assert report.pop("report_schema_version") == 2
    diagnostic = report.pop("diagnostics")
    assert ("answer_alternatives" in diagnostic) == with_alternatives
    citations = diagnostic["citation_existence"]
    assert citations["source_count"] == 50
    assert citations["baseline"]["unknown_citation_count"] == 1
    if candidate == "llama3.2-bm25-top1-v1":
        assert citations == json.loads((ROOT / "benchmarks/squad-citation-existence-v1.json").read_text())
    unknown_cases = [case for case in citations["baseline"]["cases"] if case["unknown_source_ids"]]
    assert [case["case_id"] for case in unknown_cases] == ["squad-56e17644e3433e1400422f40"]
    original.pop("report_schema_version")
    assert original == report
    markdown = (extended / "report.md").read_text()
    assert "Optional citation existence (diagnostic only)" in markdown
    assert "not relevance or support" in markdown
    assert "N/A" in markdown


@pytest.mark.parametrize("problem", ["recording", "case", "ids"])
def test_mismatched_citation_diagnostic_is_rejected_before_writing(tmp_path, problem):
    inputs = load_comparison(
        ROOT / "datasets/squad/v1/dataset.json",
        ROOT / "recordings/squad/llama3.2-bm25-v1/recording.json",
        ROOT / "recordings/squad/llama3.2-bm25-top1-v1/recording.json",
    )
    path = ROOT / "datasets/squad/v1/sources.json"
    diagnostic = build_citation_existence(inputs, load_corpus(path), corpus_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if problem == "recording":
        diagnostic.candidate.recording_id = "different"
    elif problem == "case":
        diagnostic.candidate.cases[0].case_id = "different"
    else:
        diagnostic.candidate.cases[0].unknown_source_ids = ("different",)
    output = tmp_path / "reports"
    with pytest.raises(ValueError, match="citation diagnostic.*mismatch"):
        write_reports(compare_and_gate(inputs), output, citation_existence=diagnostic)
    assert not output.exists()


def test_unknown_citation_ids_are_escaped_in_optional_markdown():
    inputs = load_comparison(
        ROOT / "datasets/support_policy/v1/dataset.json",
        ROOT / "recordings/baseline.synthetic.v1.json",
        ROOT / "recordings/candidate.synthetic.v2.json",
    )
    # Keep case coverage intact while adding an invalid observation for this test.
    inputs.candidate.responses[0].cited_source_ids = ["<script>|[bad](url)"]
    path = ROOT / "datasets/support_policy/v1/sources.json"
    diagnostic = build_citation_existence(inputs, load_corpus(path), corpus_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    text = render_markdown(compare_and_gate(inputs), citation_existence=diagnostic)
    assert "<script>" not in text
    section = text.split("## Optional citation existence", 1)[1]
    assert r"&lt;script&gt;\|\[bad\]\(url\)" in section


def test_missing_diagnostic_corpus_returns_execution_error_without_reports(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_bytes((ROOT / "datasets/support_policy/v1/dataset.json").read_bytes())
    output = tmp_path / "reports"
    process = subprocess.run([
        sys.executable, "-m", "llm_reliability", "--dataset", str(dataset),
        "--baseline", str(ROOT / "recordings/baseline.synthetic.v1.json"),
        "--candidate", str(ROOT / "recordings/candidate.synthetic.v2.json"),
        "--citation-existence", "--output-dir", str(output),
    ], capture_output=True, text=True)
    assert process.returncode == 2
    assert "citation existence" in process.stderr
    assert str(tmp_path / "sources.json") in process.stderr
    assert not output.exists()
