# Submission Cleanup Plan — Sprint 7.1

**Date:** 2026-05-27
**Sprint 7 authoritative baseline:** report_05aacb872fda | PARTIAL_PASS | 49/50 facts | pulse_score=55.8

---

## Objective

Transform the accumulated development repository into a clean, judge-readable submission state while preserving all authoritative Sprint 7 / Sprint 7.1 evidence, Sprint 5 baseline, and full source code.

---

## Hard Constraints

- Do NOT delete source code
- Do NOT delete `.env`
- Do NOT delete `backend/data/pulselns.db`
- Do NOT delete Sprint 7 / Sprint 7.1 authoritative artifacts
- Do NOT delete Sprint 5 baseline artifacts
- Archive stale files instead of deleting them
- Do NOT run the pipeline
- Do NOT call Bright Data or OpenRouter
- Do NOT change backend pipeline logic
- Do NOT modify LangGraph, Quality Gate thresholds, Agent logic, or schemas
- Do NOT remove Sprint 7 Agent 1 signal balance fix
- Do NOT remove Sprint 5 expansion stability fix

---

## Part A: Source Hygiene

Three source-level changes identified by audit (`SOURCE_HYGIENE_AUDIT_REPORT.md`):

| Action | File | Change |
|---|---|---|
| Move | `backend/app/pipeline/test_a2_a3.py` | → `backend/scripts/test_a2_a3.py` |
| Update | `backend/scripts/evidence_quality_audit.py` L49-50 | Stale report_id → `report_05aacb872fda` |
| Update | `backend/scripts/pricing_document_extraction_diagnosis.py` L46-47 | Stale report_id → `report_05aacb872fda` |

Post-change verification (all must pass before Part B):
1. `cd backend && python -c "from app.pipeline import graph; print('OK')"`
2. `cd backend && python scripts/test_agent1_expansion_stability.py`
3. `cd backend && python scripts/test_agent1_signal_balance.py`

---

## Part B: Artifact and Doc Cleanup

### Root-level .md files retained (14)

README.md, ARCHITECTURE.md, JUDGE_READINESS_ASSESSMENT_SPRINT_7.md,
SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md, AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md,
BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md, FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md,
SPRINT_7_REGRESSION_COMPARISON.md, SOURCE_HYGIENE_AUDIT_REPORT.md,
SUBMISSION_CLEANUP_PLAN.md, SUBMISSION_ARTIFACT_INDEX.md, CLEANUP_MANIFEST.md,
ARCHITECTURE.pdf, idea.pdf

### Root-level .md files archived (36 → docs/archive_sprints/)

All sprint implementation plans, all pre-Sprint-7 authoritative artifact indexes,
all sprint review and changelog docs. Full list in `CLEANUP_MANIFEST.md`.

### Judge-facing docs copied (8 → docs/submission/)

JUDGE_READINESS_ASSESSMENT_SPRINT_7.md, SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md,
AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md, BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md,
FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md, SPRINT_7_REGRESSION_COMPARISON.md,
SUBMISSION_ARTIFACT_INDEX.md, SUBMISSION_CLEANUP_PLAN.md

### Pipeline artifact dirs retained (5 + README.md)

sprint7_review_bundle_20260527T001729Z/ (authoritative),
demo_track2_20260526T165950Z/ (Sprint 7 pipeline run),
evidence_quality_20260526T171620Z/ (Sprint 7 evidence audit),
sprint7_signal_balance_tests_20260526T165738Z/ (Sprint 7 static tests),
sprint5_review_bundle_20260526T081013Z/ (Sprint 5 baseline reference)

### Pipeline artifact dirs archived (23 → archive_pre_submission_<ts>/)

All Sprint 2-6 runs, intermediate Sprint 7 runs, and pre-submission archives.
Full list in `CLEANUP_MANIFEST.md`.

### Safe deletions

`backend/app/**/__pycache__/`, `backend/scripts/__pycache__/`, `.pytest_cache/`

---

## Rollback

```bash
# Source changes
git checkout -- backend/scripts/evidence_quality_audit.py \
                backend/scripts/pricing_document_extraction_diagnosis.py
git mv backend/scripts/test_a2_a3.py backend/app/pipeline/test_a2_a3.py

# Doc moves
mv docs/archive_sprints/*.md .

# Artifact moves
mv pipeline_audit_artifacts/archive_pre_submission_*/* pipeline_audit_artifacts/
```

`__pycache__` directories auto-regenerate on the next Python run.
All moved files are listed in `CLEANUP_MANIFEST.md`.
