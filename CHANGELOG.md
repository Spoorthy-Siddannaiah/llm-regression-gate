# Changelog

## Unreleased audit hardening

- Frozen recorder input bytes and pre-completion drift checks.
- Sanitized provider error categories/locations without raw response logging.
- Neutral report-origin wording, duplicate-key rejection, and corpus reference checks.
- Report schema 4: paired case changes and CLI evaluation provenance receipts.
- Optional `max_regressed_cases`; existing gate decisions preserved when omitted.
- Verified action SHA pins, Ubuntu 24.04, and pinned build requirements.
- No historical dataset, recording, policy threshold, or baseline changed.
- No license added, commits created, or publication performed.

## 0.1.0 — local release candidate, 2026-11-09

- Typed, versioned datasets and recorded baseline/candidate comparisons.
- Deterministic phrase, citation-label, and retrieval checks; critical-case guards.
- Absolute/relative gates plus v2 unknown-citation enforcement.
- JSON/Markdown reports; exit 0 pass, 1 quality failure, 2 execution/input error.
- Optional local BM25/Ollama generation with raw evidence, manifests, code targets,
  and freshness validation. Baselines remain fixed.
- Actual SQuAD retrieval-depth regression and controlled citation-schema fix,
  both reproducible by offline replay.
- GitHub Actions configuration for tests and eight known-outcome replay checks.
- Architecture, demo runbook, provenance documentation, and interview questions.

Hosted CI is unverified until publication. Automatic PR-driven inference, clinical
documentation evaluation, live observability, and deployment remain future work.
Original project code remains unlicensed at the owner's request. Adapted SQuAD
data retains its separate CC BY-SA 4.0 notice.
