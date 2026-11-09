"""Deterministic report rendering and explicit, non-overwriting file output."""

import html
import json
from pathlib import Path
import re

from llm_reliability.gates import GateResult, GateResultV2, build_case_changes
from llm_reliability.alternative_diagnostics import AlternativesDiagnostic
from llm_reliability.citation_existence import CitationExistenceDiagnostic
from llm_reliability.evaluation_receipt import EvaluationReceipt


class ReportWriteError(OSError):
    """Report output failed; inspect the named directory for partial artifacts."""


def _validate_diagnostic(result: GateResult, diagnostic: AlternativesDiagnostic) -> None:
    for role in ("baseline", "candidate"):
        evaluation = getattr(result.evaluation, role)
        summary = getattr(diagnostic.results, role)
        expected = [(case.case_id, case.all_required_facts_present) for case in evaluation.cases]
        observed = [(case.case_id, case.required_facts_present_v1) for case in summary.cases]
        if summary.recording_id != evaluation.recording_id or expected != observed:
            raise ValueError(f"{role}: alternative diagnostic does not match gate evaluation")
        if diagnostic.case_count != len(expected):
            raise ValueError(f"{role}: alternative diagnostic case count mismatch")


def _validate_citation_diagnostic(result: GateResult, diagnostic: CitationExistenceDiagnostic) -> None:
    if isinstance(result, GateResultV2) and diagnostic != result.citation_existence_gate.diagnostic:
        raise ValueError("citation diagnostic disagrees with enforced v2 evidence")
    for role in ("baseline", "candidate"):
        evaluation = getattr(result.evaluation, role)
        summary = getattr(diagnostic, role)
        if summary.recording_id != evaluation.recording_id:
            raise ValueError(f"{role}: citation diagnostic recording mismatch")
        if [case.case_id for case in summary.cases] != [case.case_id for case in evaluation.cases]:
            raise ValueError(f"{role}: citation diagnostic case mismatch")
        for case, evidence in zip(evaluation.cases, summary.cases, strict=True):
            cited = set(case.citations.relevant_cited_source_ids + case.citations.unlabelled_cited_source_ids)
            if cited != set(evidence.existing_source_ids + evidence.unknown_source_ids):
                raise ValueError(f"{role}/{case.case_id}: citation diagnostic ID mismatch")


def render_json(
    result: GateResult, *, answer_alternatives: AlternativesDiagnostic | None = None,
    citation_existence: CitationExistenceDiagnostic | None = None,
    provenance: EvaluationReceipt | None = None,
) -> str:
    payload = {"report_schema_version": 4, **result.model_dump(mode="json"),
               "case_changes": [case.model_dump(mode="json") for case in build_case_changes(result.evaluation)],
               "provenance": provenance.model_dump(mode="json") if provenance else None}
    _validate_receipt(result, provenance)
    if answer_alternatives is not None:
        _validate_diagnostic(result, answer_alternatives)
        payload["report_schema_version"] = max(2, payload["report_schema_version"])
        payload["diagnostics"] = {"answer_alternatives": answer_alternatives.model_dump(mode="json")}
    if citation_existence is not None:
        _validate_citation_diagnostic(result, citation_existence)
        payload["report_schema_version"] = max(2, payload["report_schema_version"])
        payload.setdefault("diagnostics", {})["citation_existence"] = citation_existence.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _text(value: object) -> str:
    # Render fixture values as text rather than executable HTML or Markdown syntax.
    escaped = re.sub(r"([\\`*_\[\]{}()#+.!|~-])", r"\\\1", str(value))
    escaped = html.escape(escaped, quote=False)
    return "<br>".join(escaped.splitlines())


def _items(values: tuple[str, ...]) -> str:
    return "; ".join(_text(value) for value in values) if values else "None"


def render_markdown(
    result: GateResult, *, answer_alternatives: AlternativesDiagnostic | None = None,
    citation_existence: CitationExistenceDiagnostic | None = None,
    provenance: EvaluationReceipt | None = None,
) -> str:
    _validate_receipt(result, provenance)
    if answer_alternatives is not None:
        _validate_diagnostic(result, answer_alternatives)
    if citation_existence is not None:
        _validate_citation_diagnostic(result, citation_existence)
    evaluation = result.evaluation
    lines = [
        "# Regression evaluation report", "",
        f"**Gate: {'PASS' if result.passed else 'FAIL'}**", "",
        "Report schema: 4", "",
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
    lines.extend(["", "## Per-case metric changes", "",
                  "Regressed takes precedence when a case has both improvements and regressions. "
                  "Critical highlights are evidence; enforcement follows the selected policy.", "",
                  "| Case | Status | Critical regression | Metric | Baseline | Candidate | Delta |",
                  "| --- | --- | --- | --- | ---: | ---: | ---: |"])
    for case in build_case_changes(evaluation):
        for metric in case.metrics:
            lines.append(f"| {_text(case.case_id)} | {case.status} | {case.critical_regression} | "
                         f"{metric.metric} | {metric.baseline:.6f} | {metric.candidate:.6f} | {metric.delta:+.6f} |")
    if result.policy.max_regressed_cases is not None:
        lines.extend(["", f"Maximum regressed cases: {result.policy.max_regressed_cases}"])
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
    if isinstance(result, GateResultV2):
        evidence = result.citation_existence_gate
        limits = result.policy.unknown_citations
        lines.extend([
            "", "## Enforced unknown-citation gate", "",
            "This v2 policy enforces corpus membership counts, not relevance or semantic support. "
            "Counts are citation occurrences across cases. Missing citations are not unknown IDs.", "",
            f"Maximum candidate unknown citations: {limits.max_candidate_unknown}; "
            f"maximum increase: {limits.max_increase}", "",
            f"Corpus SHA-256: {_text(evidence.diagnostic.corpus_sha256)}", "",
            "| Baseline unknown | Candidate unknown | Candidate minus baseline |",
            "| ---: | ---: | ---: |",
            f"| {evidence.baseline_unknown_count} | {evidence.candidate_unknown_count} | {evidence.increase:+d} |", "",
            "| Recording | Case | Unknown cited IDs |", "| --- | --- | --- |",
        ])
        for role in ("baseline", "candidate"):
            unknown_cases = [case for case in getattr(evidence.diagnostic, role).cases if case.unknown_source_ids]
            if not unknown_cases:
                lines.append(f"| {role} | None | None |")
            for case in unknown_cases:
                lines.append(f"| {role} | {_text(case.case_id)} | {_items(case.unknown_source_ids)} |")
    if answer_alternatives is not None:
        lines.extend([
            "", "## Optional answer alternatives (diagnostic only)", "",
            "This evidence does not change the gate decision, thresholds, or failure reasons. "
            "Any listed phrase may match; this is not semantic correctness scoring.", "",
            f"Diagnostic evaluator: {_text(answer_alternatives.evaluator_version)}", "",
            "| Recording | Required-fact case coverage v1 | Any-alternative case coverage |",
            "| --- | ---: | ---: |",
        ])
        for role in ("baseline", "candidate"):
            summary = getattr(answer_alternatives.results, role)
            lines.append(f"| {role} | {summary.required_fact_case_coverage_v1:.6f} | {summary.alternative_case_coverage:.6f} |")
        for role in ("baseline", "candidate"):
            summary = getattr(answer_alternatives.results, role)
            lines.extend([
                "", f"### {role.capitalize()} alternative evidence", "",
                "| Case | Allowed alternatives | Matched | Unmatched | Any present |",
                "| --- | --- | --- | --- | --- |",
            ])
            for case in summary.cases:
                evidence = case.alternative_result
                lines.append(
                    f"| {_text(case.case_id)} | {_items(tuple(case.alternatives))} "
                    f"| {_items(evidence.matched_alternatives)} | {_items(evidence.unmatched_alternatives)} "
                    f"| {evidence.any_alternative_present} |"
                )
        lines.extend(["", "Diagnostic input SHA-256:", ""])
        for name, digest in answer_alternatives.input_sha256.items():
            lines.append(f"- {_text(name)}: {_text(digest)}")
    if citation_existence is not None:
        lines.extend([
            "", "## Optional citation existence (diagnostic only)", "",
            "Existence is exact ID membership in the supplied corpus snapshot, not relevance "
            "or support for the answer. Unknown IDs may be invented, mistyped, or external "
            "to this corpus; the cause is not established. This does not change the gate.", "",
            f"Evaluator: {_text(citation_existence.evaluator_version)}; sources: {citation_existence.source_count}", "",
            f"Corpus SHA-256: {_text(citation_existence.corpus_sha256)}", "",
            "| Recording | Existing citations | Unknown citations | Cases without citations |",
            "| --- | ---: | ---: | ---: |",
        ])
        for role in ("baseline", "candidate"):
            summary = getattr(citation_existence, role)
            lines.append(f"| {role} | {summary.existing_citation_count} | {summary.unknown_citation_count} | {summary.cases_without_citations} |")
        for role in ("baseline", "candidate"):
            lines.extend([
                "", f"### {role.capitalize()} citation existence evidence", "",
                "| Case | Existing IDs | Unknown IDs | All cited IDs exist |",
                "| --- | --- | --- | --- |",
            ])
            for case in getattr(citation_existence, role).cases:
                state = str(case.all_cited_ids_exist) if case.has_citations else "N/A (no citations)"
                lines.append(f"| {_text(case.case_id)} | {_items(case.existing_source_ids)} | {_items(case.unknown_source_ids)} | {_text(state)} |")
    lines.extend([
        "", "## Interpretation and limits", "",
        (
            "Required-phrase checks do not establish semantic correctness. Citation-ID "
            "checks do not establish source existence or support. Relevance labels may "
            "be incomplete. Displayed numbers are rounded; JSON preserves numeric values."
            if citation_existence is None and not isinstance(result, GateResultV2) else
            "Required-phrase checks do not establish semantic correctness. Citation existence "
            "does not establish relevance or support. Relevance labels may be incomplete. "
            "Displayed numbers are rounded; JSON preserves numeric values."
        ), "",
        (
            "This report does not establish whether recordings are synthetic or real model "
            "outputs; consult recording provenance. Recording origin is not inferred "
            "from scores. Versions are manual labels, not content hashes. "
            "The baseline was not automatically replaced."
            if answer_alternatives is None and citation_existence is None and not isinstance(result, GateResultV2) else
            "Consult recording provenance for the origin of recorded outputs. Diagnostic "
            "input hashes identify the files used; they do not establish semantic correctness "
            "or signed authenticity. The baseline was not automatically replaced."
        ),
    ])
    lines.extend(["", "## Evaluation provenance receipt", ""])
    if provenance is None:
        lines.append("Not supplied by this API caller; input-byte identity was not recorded in this report.")
    else:
        lines.extend([f"Evaluator: {_text(provenance.evaluator_version)}; policy: {_text(provenance.policy_version)}",
                      f"Code-target validation: {provenance.code_target_validation}", "",
                      "Hashes identify bytes, not signed authenticity or current-PR execution.", "",
                      "| Input | SHA-256 |", "| --- | --- |"])
        for name, digest in sorted(provenance.input_sha256.items()):
            lines.append(f"| {_text(name)} | {digest} |")
        lines.extend(["", "Evaluator source SHA-256:", ""])
        for name, digest in sorted(provenance.evaluator_source_sha256.items()):
            lines.append(f"- {_text(name)}: {digest}")
    return "\n".join(lines) + "\n"


def _validate_receipt(result: GateResult, receipt: EvaluationReceipt | None) -> None:
    if receipt is not None and (receipt.evaluator_version != result.evaluation.settings.evaluator_version
                                or receipt.policy_version != result.policy.policy_version):
        raise ValueError("provenance receipt versions do not match evaluation")


def write_reports(
    result: GateResult, output_directory: str | Path,
    *, answer_alternatives: AlternativesDiagnostic | None = None,
    citation_existence: CitationExistenceDiagnostic | None = None,
    provenance: EvaluationReceipt | None = None,
) -> tuple[Path, Path]:
    """Write into a NEW directory; refuse existing directories to prevent overwrites.

    Render before touching disk. The two-file write is not atomic; a disk error may
    leave partial output. Errors name the directory; choose a new directory to retry.
    """
    json_content = render_json(result, answer_alternatives=answer_alternatives, citation_existence=citation_existence, provenance=provenance)
    markdown_content = render_markdown(result, answer_alternatives=answer_alternatives, citation_existence=citation_existence, provenance=provenance)
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
