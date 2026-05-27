# Submission Artifact Index

**Date:** 2026-05-27
**Sprint 7 authoritative baseline:** report_05aacb872fda | PARTIAL_PASS | 49/50 facts | pulse_score=55.8

---

## Judge-Facing Documents (root level)

| Document | Purpose |
|---|---|
| `README.md` | Project overview and setup |
| `ARCHITECTURE.md` | System architecture reference |
| `ARCHITECTURE.pdf` | Architecture diagram |
| `idea.pdf` | Original project concept |
| `JUDGE_READINESS_ASSESSMENT_SPRINT_7.md` | Safe/unsafe claims, demo narrative, evidence panels, limitations |
| `SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md` | Full audit: suspicious count explanation, domain bug fix, per-signal fact analysis |
| `AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md` | Sprint 7.1 artifact index and corrected source tier summary |
| `BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md` | Sprint 7 query planning changes, signal balance telemetry |
| `FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md` | Stage-by-stage pipeline execution trace |
| `SPRINT_7_REGRESSION_COMPARISON.md` | Sprint 4/5/6/7 side-by-side comparison, rollback assessment |
| `SOURCE_HYGIENE_AUDIT_REPORT.md` | Source hygiene scan results and actions taken |
| `SUBMISSION_CLEANUP_PLAN.md` | Cleanup plan with constraints and rollback instructions |
| `SUBMISSION_ARTIFACT_INDEX.md` | This file |
| `CLEANUP_MANIFEST.md` | Complete list of all moved/archived files |

---

## docs/submission/ (Copies for Easy Judge Access)

| Document | Purpose |
|---|---|
| `JUDGE_READINESS_ASSESSMENT_SPRINT_7.md` | Primary judge document: what can/cannot be claimed, demo narrative |
| `SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md` | Evidence audit with code bug documentation |
| `AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md` | Sprint 7.1 authoritative index |
| `BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md` | Query planning architecture |
| `FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md` | Full pipeline execution trace |
| `SPRINT_7_REGRESSION_COMPARISON.md` | Regression table vs prior sprints |
| `SUBMISSION_ARTIFACT_INDEX.md` | This file (copy) |
| `SUBMISSION_CLEANUP_PLAN.md` | Cleanup plan (copy) |

---

## Authoritative Pipeline Artifacts

### sprint7_review_bundle_20260527T001729Z/ (primary)

The canonical Sprint 7 review bundle. Contains all pipeline artifacts plus all Sprint 7 and Sprint 7.1 documents.

| File | Contents |
|---|---|
| `evidence_quality_summary.json` | Top-level quality metrics (suspicious_claim_count=0, avg_confidence=0.931) |
| `signal_semantics_audit.json` | Per-signal vocabulary checks (17 vocab mismatches — NOT fabrications) |
| `suspicious_claims.json` | Fabrication-pattern check output (empty array — 0 fabrications) |
| `source_tier_quality_audit.json` | Domain tier classification (4 auth, 7 acceptable, 1 suspicious) |
| `pricing_pressure_semantics_audit.json` | Pricing fact classification (2 facts, strong_pricing_signal, $6.00/GPU-hr) |
| `quality_gate_audit.json` | Quality gate round decisions |
| `final_report_quality_summary.json` | Report metadata, pulse_score=55.8, watch list |
| `query_planner_audit.json` | Query telemetry (42 queries, 15 playbook, B6 telemetry) |
| `web_collection_audit.json` | Fetch stats (61 accepted docs, 131 Bright Data calls, 28.57% zero-doc rate) |
| `demo_report_summary.json` | Pipeline run summary |

### demo_track2_20260526T165950Z/ (Sprint 7 pipeline run)

Raw pipeline output for report_05aacb872fda. All intermediate agent outputs.

### evidence_quality_20260526T171620Z/ (Sprint 7 evidence audit)

Output of evidence_quality_audit.py run against Sprint 7. Source of the sprint7_review_bundle JSON files.

### sprint7_signal_balance_tests_20260526T165738Z/ (final)

Sprint 7 static signal balance test results. Confirms structural minimums enforced without live API calls.

### sprint5_review_bundle_20260526T081013Z/ (Sprint 5 baseline)

Sprint 5 authoritative baseline artifacts for regression comparison. 40 facts, 19 sources, pulse_score=53.6.

---

## Archived Artifacts

All pre-Sprint-7 pipeline runs and intermediate Sprint 7 runs moved to:
`pipeline_audit_artifacts/archive_pre_submission_<timestamp>/`

All prior sprint documents (Sprints 2-6) moved to:
`docs/archive_sprints/`

Full list of archived files: `CLEANUP_MANIFEST.md`

---

## Source Code

| Directory | Contents |
|---|---|
| `backend/app/pipeline/` | LangGraph agents (1-8), graph.py, quality_gate.py — no test files |
| `backend/app/utils/` | url_scorer.py, helpers, llm_client, brightdata_client |
| `backend/app/config/` | Settings, signal/company/scope definitions |
| `backend/app/api/` | FastAPI routes |
| `backend/app/schemas/` | Pydantic models |
| `backend/scripts/` | 3 primary entrypoints: demo_track2, evidence_quality_audit, pricing_diagnosis |
| `backend/scripts/diagnostics/` | 3 live diagnostic scripts (require API keys) |
| `backend/scripts/archive_pre_submission/` | Archived test_a2_a3.py (live A2→A3 integration test) |
| `backend/tests/` | test_chat.py, test_pipeline_live.py, test_pipeline_quality.py |
| `backend/tests/pipeline/` | Zero-cost static tests: test_agent1_expansion_stability.py (4 tests), test_agent1_signal_balance.py (15 tests) |
| `frontend/` | React frontend |

Key Sprint 7 change: `backend/app/pipeline/agent1_query_planner.py` — signal balance minimums, caps, domain-specificity rules, targeted regeneration, B6 telemetry. No other pipeline files modified in Sprint 7.

See `CLEAN_REPOSITORY_STRUCTURE.md` for the full annotated directory tree.
