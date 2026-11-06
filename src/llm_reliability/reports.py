"""Deterministic report rendering and explicit, non-overwriting file output."""

import html
import json
from pathlib import Path
import re

from llm_reliability.gates import GateResult


class ReportWriteError(OSError):
    """Report output failed; inspect the named directory for partial artifacts."""


def render_json(result: GateResult) -> str:
    payload = {"report_schema_version": 1, **result.model_dump(mode="json")}
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _text(value: object) -> str:
    # Render fixture values as text rather than executable HTML or Markdown syntax.
    escaped = re.sub(r"([\\`*_\[\]{}()#+.!|~-])", r"\\\1", str(value))
    escaped = html.escape(escaped, quote=False)
    return "<br>".join(escaped.splitlines())


def _items(values: tuple[str, ...]) -> str:
    return "; ".join(_text(value) for value in values) if values else "None"


def render_markdown(result: GateResult) -> str:
    evaluation = result.evaluation
    lines = [
        "# Regression evaluation report", "",
        f"**Gate: {'PASS' if result.passed else 'FAIL'}**", "",
        "Report schema: 1", "",
        f"Dataset: {_text(evaluation.dataset_id)} / {_text(evaluation.dataset_version)} "
        f"(schema {evaluation.dataset_schema_version})", "",
        f"Evaluator: {_text(evaluation.settings.evaluator_version)}; "
        f"retrieval K: {evaluation.settings.retrieval_k}", "",
        f"Policy: {_text(result.policy.policy_version)}; require critical facts: "
        f"{result.policy.require_critical_facts}", "",
        "## Metric comparison", "",
        "Values are fractions in [0, 1]; delta = candidate minus baseline. "
        "Means weight cases equally. Threshold equality passes (tolerance 1e-12).", "",
        "| Metric | Baseline | Candidate | Delta | Minimum | Allowed drop |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in result.metrics:
        threshold = getattr(result.policy, metric.metric)
        lines.append(
            f"| {_text(metric.metric)} | {metric.baseline:.6f} | {metric.candidate:.6f} "
            f"| {metric.delta:+.6f} | {threshold.minimum:.6f} | {threshold.max_drop:.6f} |"
        )
    lines.extend(["", "## Gate failures", ""])
    if result.failures:
        for failure in result.failures:
            lines.append(
                f"- {_text(failure.code)} / {_text(failure.metric)} / "
                f"{_text(failure.case_id) if failure.case_id else 'aggregate'}: {_text(failure.message)}"
            )
    else:
        lines.append("None.")
    for role, recording in (("Baseline", evaluation.baseline), ("Candidate", evaluation.candidate)):
        lines.extend([
            "", f"## {role}", "", f"Recording: {_text(recording.recording_id)}", "",
            "| Configuration field | Value |", "| --- | --- |",
        ])
        for key, value in recording.configuration.model_dump().items():
            lines.append(f"| {_text(key)} | {_text(value)} |")
        for case in recording.cases:
            lines.extend([
                "", f"### Case: {_text(case.case_id)}", "",
                f"Criticality: {_text(case.criticality.value)}", "",
                f"- All required phrases present: {case.all_required_facts_present}",
                f"- Matched phrases: {_items(case.required_facts.matched_facts)}",
                f"- Missing phrases: {_items(case.required_facts.missing_facts)}",
                f"- Relevant cited IDs: {_items(case.citations.relevant_cited_source_ids)}",
                f"- Unlabelled cited IDs: {_items(case.citations.unlabelled_cited_source_ids)}",
                f"- Missing relevant citation IDs: {_items(case.citations.missing_relevant_source_ids)}",
                f"- Retrieved IDs at K (ranked): {_items(case.retrieval.retrieved_source_ids_at_k)}",
                f"- Found relevant retrieval IDs: {_items(case.retrieval.found_relevant_source_ids)}",
                f"- Missing relevant retrieval IDs: {_items(case.retrieval.missing_relevant_source_ids)}",
                f"- Recall@{case.retrieval.k}: {case.retrieval_recall_at_k:.6f}",
            ])
    lines.extend([
        "", "## Interpretation and limits", "",
        "Required-phrase checks do not establish semantic correctness. Citation-ID "
        "checks do not establish source existence or support. Relevance labels may "
        "be incomplete. Displayed numbers are rounded; JSON preserves numeric values.", "",
        "This report does not establish whether recordings are synthetic or real model "
        "outputs; consult recording provenance. The repository's bundled recordings "
        "are synthetic fixtures. Versions are manual labels, not content hashes. "
        "The baseline was not automatically replaced.",
    ])
    return "\n".join(lines) + "\n"


def write_reports(result: GateResult, output_directory: str | Path) -> tuple[Path, Path]:
    """Write into a NEW directory; refuse existing directories to prevent overwrites.

    Render before touching disk. The two-file write is not atomic; a disk error may
    leave partial output. Errors name the directory; choose a new directory to retry.
    """
    json_content = render_json(result)
    markdown_content = render_markdown(result)
    directory = Path(output_directory)
    json_path = directory / "report.json"
    markdown_path = directory / "report.md"
    try:
        directory.mkdir(parents=True, exist_ok=False)
        with json_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json_content)
        with markdown_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(markdown_content)
    except OSError as error:
        raise ReportWriteError(
            f"{directory}: cannot write reports: {error}. Existing output is never "
            "overwritten; inspect for partial artifacts and retry with a new directory."
        ) from error
    return json_path, markdown_path
