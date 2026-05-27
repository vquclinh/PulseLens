# Cleanup Manifest — Sprint 7.1 Submission Cleanup

**Date:** 2026-05-27
**Operation:** Pre-submission repo cleanup. Archive stale files; no deletions of source code or authoritative artifacts.

---

## Root .md Files Archived → docs/archive_sprints/

| File | Reason |
|---|---|
| `AGENT1_EXPANSION_STABILITY_SPRINT_5_REPORT.md` | Sprint 5 sub-report — covered by regression comparison |
| `AGENT1_SIGNAL_DISTRIBUTION_AUDIT_SPRINT_7.md` | Superseded by Sprint 7 balanced query planning report |
| `AGENT_QUALITY_REPORT.md` | Early sprint quality report, superseded |
| `AUTHORITATIVE_FULL_REGRESSION_ARTIFACTS.md` | Superseded by Sprint 7.1 authoritative artifacts |
| `AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` | Sprint 2 historical |
| `AUTHORITATIVE_SPRINT_3_ARTIFACTS.md` | Sprint 3 historical |
| `AUTHORITATIVE_SPRINT_4_ARTIFACTS.md` | Sprint 4 historical |
| `AUTHORITATIVE_SPRINT_5_ARTIFACTS.md` | Sprint 5 baseline in sprint5_review_bundle (superseded at root) |
| `AUTHORITATIVE_SPRINT_7_ARTIFACTS.md` | Superseded by AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md |
| `CLEAN_FULL_REGRESSION_PLAN.md` | Planning doc — execution complete |
| `CLEANUP_BEFORE_SPRINT5_MANIFEST.md` | Old cleanup manifest |
| `CURRENT_PIPELINE_RUN_STATUS.md` | Pipeline run tracking — Sprint 7 complete |
| `EVIDENCE_CLEANUP_SPRINT_4_REPORT.md` | Sprint 4 historical |
| `EVIDENCE_QUALITY_SPRINT_3_REPORT.md` | Sprint 3 historical |
| `FULL_PIPELINE_TEST_REPORT.md` | Early test report, superseded |
| `FULL_REGRESSION_WEAKNESS_REPORT.md` | Pre-Sprint-7 weakness analysis, resolved |
| `idea.md` | Draft notes — `idea.pdf` is the authoritative version |
| `PRICING_PRESSURE_FAILURE_ANALYSIS.md` | Sprint 3/4 issue, resolved in Sprint 7 |
| `PRICING_PRESSURE_RETRIEVAL_SPRINT_2_REPORT.md` | Sprint 2 historical |
| `PROJECT_CURRENT_STATE_SUMMARY.md` | Status tracking — superseded |
| `PROJECT_STATUS.md` | Status tracking — superseded |
| `RETRIEVAL_QUALITY_STABILIZATION_REPORT.md` | Pre-Sprint-7 analysis, resolved |
| `SPRINT_2_CHANGELOG_AND_RISK_CHECK.md` | Sprint 2 historical |
| `SPRINT_2_IMPLEMENTATION_PLAN.md` | Sprint 2 historical |
| `SPRINT_3_IMPLEMENTATION_PLAN.md` | Sprint 3 historical |
| `SPRINT_4_BEFORE_AFTER_COMPARISON.md` | Sprint 4 historical |
| `SPRINT_4_IMPLEMENTATION_PLAN.md` | Sprint 4 historical |
| `SPRINT_5_CLEAN_START_PLAN.md` | Sprint 5 historical |
| `SPRINT_5_HARDCODE_SCAN_RESULTS.md` | Sprint 5 historical |
| `SPRINT_5_INTEGRITY_AUDIT_PLAN.md` | Sprint 5 historical |
| `SPRINT_5_INTEGRITY_AUDIT_REPORT.md` | Sprint 5 historical — summary in regression comparison |
| `SPRINT_5_REGRESSION_COMPARISON.md` | Superseded by full Sprint 7 regression comparison |
| `SPRINT_5_TEST_QUALITY_REVIEW.md` | Sprint 5 historical |
| `SPRINT_7_1_RECONCILIATION_PLAN.md` | Planning doc — execution complete, findings in reconciliation report |
| `SPRINT_7_IMPLEMENTATION_PLAN.md` | Planning doc — Sprint 7 execution complete |

---

## Pipeline Artifact Dirs Archived → pipeline_audit_artifacts/archive_pre_submission_<ts>/

| Directory | Reason |
|---|---|
| `agent1_expansion_test_20260526T075733Z` | Sprint 5 intermediate test run |
| `archive_before_full_regression_20260526T065615Z` | Pre-Sprint-5 archive |
| `archive_before_sprint5_20260526T075113Z` | Pre-Sprint-5 archive |
| `archive_sprint2_stale` | Sprint 2 stale artifacts |
| `archive_sprint4_stale` | Sprint 4 stale artifacts |
| `demo_track2_20260526T040110Z` | Sprint 5/6 pipeline run — superseded by Sprint 7 |
| `demo_track2_20260526T063140Z` | Sprint 6 intermediate run |
| `demo_track2_20260526T075840Z` | Sprint 6 intermediate run |
| `demo_track2_20260526T093932Z` | Sprint 6 intermediate run |
| `demo_track2_20260526T155555Z` | Sprint 7 pre-authoritative run |
| `evidence_quality_20260526T053621Z` | Sprint 5/6 evidence quality run |
| `evidence_quality_20260526T071826Z` | Sprint 6 evidence quality run |
| `evidence_quality_20260526T080855Z` | Sprint 6 evidence quality run |
| `evidence_quality_20260526T095106Z` | Sprint 6 evidence quality run |
| `evidence_quality_20260526T160803Z` | Sprint 7 pre-authoritative evidence quality run |
| `full_regression_20260526T065737Z` | Sprint 5 regression run |
| `pricing_extraction_diagnosis_20260526T071833Z` | Sprint 5/6 pricing diagnosis |
| `pricing_pressure_20260526T033831Z` | Sprint 2/3 pricing pressure run |
| `sprint5_integrity_audit_20260526T090117Z` | Sprint 5 integrity audit |
| `sprint6_review_bundle_20260526T095409Z` | Sprint 6 review bundle — Sprint 6 superseded |
| `sprint6_static_tests_20260526T095344Z` | Sprint 6 static tests |
| `sprint6_superseded_artifacts` | Sprint 6 superseded artifacts |
| `sprint7_signal_balance_tests_20260526T164856Z` | Sprint 7 intermediate balance test — superseded by T165738Z |

---

## Source Files Changed — Pass 1

| File | Change |
|---|---|
| `backend/app/pipeline/test_a2_a3.py` | MOVED to `backend/scripts/test_a2_a3.py` (Pass 1); then to `backend/scripts/archive_pre_submission/test_a2_a3.py` (Pass 2) |
| `backend/scripts/evidence_quality_audit.py` L49-50 | DEFAULT_REPORT_ID updated to `report_05aacb872fda`; DEFAULT_ARTIFACT_DIR updated to `demo_track2_20260526T165950Z` |
| `backend/scripts/pricing_document_extraction_diagnosis.py` L46-47 | _DEFAULT_REPORT_ID updated to `report_05aacb872fda`; _DEFAULT_ARTIFACT_DIR updated to `demo_track2_20260526T165950Z` |

---

## Source Files Changed — Pass 2 (scripts reorganization)

| File | From | To | Path fixes |
|---|---|---|---|
| `test_agent1_expansion_stability.py` | `scripts/` | `tests/pipeline/` | sys.path `".."` → `"../.."` ; artifact dir `"../.."` → `"../../.."` |
| `test_agent1_signal_balance.py` | `scripts/` | `tests/pipeline/` | sys.path `".."` → `"../.."` ; .env `".."` → `"../.."` ; artifact dir `"../.."` → `"../../.."` ; agent1 path `"../app"` → `"../../app"` |
| `full_pipeline_live_audit.py` | `scripts/` | `scripts/diagnostics/` | `BACKEND_DIR parents[1]` → `parents[2]` |
| `full_pipeline_retrieval_quality_audit.py` | `scripts/` | `scripts/diagnostics/` | `ROOT parents[2]` → `parents[3]` |
| `pricing_pressure_retrieval_audit.py` | `scripts/` | `scripts/diagnostics/` | `ROOT parents[2]` → `parents[3]` |
| `test_a2_a3.py` | `scripts/` | `scripts/archive_pre_submission/` | No path changes (archived) |

---

## Directories Created

| Directory | Purpose |
|---|---|
| `docs/submission/` | Copies of 8 judge-facing documents |
| `docs/archive_sprints/` | Archive of 35 stale sprint documents |
| `pipeline_audit_artifacts/archive_pre_submission_20260527T175900Z/` | Archive of 23 stale pipeline artifact directories |
| `backend/tests/pipeline/` | Zero-cost static pipeline regression tests |
| `backend/scripts/diagnostics/` | Useful but non-primary diagnostic scripts |
| `backend/scripts/archive_pre_submission/` | Archived live integration test |

---

## Directories Deleted

| Directory | Reason |
|---|---|
| `backend/app/**/__pycache__/` | Auto-generated bytecode cache |
| `backend/scripts/__pycache__/` | Auto-generated bytecode cache |
| `.pytest_cache/` | Auto-generated test cache |

---

## Not Changed

- `.env` — preserved
- `backend/data/pulselns.db` — preserved
- `frontend/dist/` — preserved (not rebuilding)
- All source code in `backend/app/pipeline/`, `backend/app/utils/`, `backend/app/config/`, `backend/app/api/`, `backend/app/schemas/`
- `backend/.venv/` — preserved
- Sprint 7 authoritative artifacts (sprint7_review_bundle_20260527T001729Z/, demo_track2_20260526T165950Z/, evidence_quality_20260526T171620Z/, sprint7_signal_balance_tests_20260526T165738Z/)
- Sprint 5 baseline (sprint5_review_bundle_20260526T081013Z/)
- Pipeline logic: LangGraph, Quality Gate, agents 1-8
- Sprint 7 Agent 1 signal balance fix
- Sprint 5 expansion stability fix
