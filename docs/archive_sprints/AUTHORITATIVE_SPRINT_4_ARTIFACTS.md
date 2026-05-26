# Authoritative Sprint 4 Artifacts

Sprint 4 goal: Evidence Cleanup, Entity Scope Enforcement, Post-Fix Demo Rerun.
All code fixes applied before the demo pipeline rerun.

---

## Authoritative Demo Run Folder

**Folder:** `pipeline_audit_artifacts/demo_track2_20260526T063140Z/`
**Run date:** 2026-05-26 13:31 UTC
**Cost:** ~120 BrightData calls + ~115 OpenRouter calls (2 rounds)
**Source data:** Live BrightData fetch (Sprint 4 fixes active)

### Files in this folder

| File | Contents |
|---|---|
| `pipeline_run.log` | Full pipeline console log |
| `demo_scope_config.json` | Scope: Nvidia, AMD, Supermicro, demo_scope_enabled=true |
| `query_planner_audit.json` | Agent 1 telemetry: 32 + 10 queries across 2 rounds |
| `web_collection_audit.json` | Agent 2 telemetry: accepted/rejected/fallback URLs per query |
| `quality_gate_audit.json` | quality_status, covered signals, company coverage |
| `fetch_error_summary.json` | HTTP error counts by domain and reason |
| `final_report_quality_summary.json` | Full MarketPulseReport fields |
| `demo_report_summary.json` | Summary with company/signal coverage, BrightData estimate |

### Key metrics from this run

| Metric | Value |
|---|---|
| `report_id` | `report_3dfb4b94068b` |
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | fact_count 43 < 50 |
| `pulse_score` | 57.0 |
| `evidence_count` | 43 |
| `source_count` | 17 |
| `covered_signal_types` | investor_signal, product_launch, pricing_pressure, strategic_messaging, supplier_risk, hiring_momentum |
| `missing_signal_types` | (none) |
| `company_coverage` | 100% |
| `query_expansion_rounds` | 1 |

---

## Authoritative Evidence Quality Audit Folder

**Folder:** `pipeline_audit_artifacts/evidence_quality_20260526T064101Z/`
**Run date:** 2026-05-26 06:41 UTC
**Cost:** Zero (DB read only)
**Source data:** Report `report_3dfb4b94068b`

### Key metrics from this audit

| Metric | Value |
|---|---|
| Total facts analyzed | 43 |
| Total verified claims | 7 |
| Average confidence | 0.956 |
| Pricing strong / weak / misclassified | 4 / 0 / 0 |
| Pricing verdict | ACCEPTABLE (100% strong) |
| Suspicious claims confirmed | 0 |
| Out-of-scope source domains | 0 |

---

## Authoritative Pricing Gap Diagnosis Folder

**Folder:** `pipeline_audit_artifacts/pricing_extraction_diagnosis_20260526T061730Z/`
**Run date:** 2026-05-26 06:17 UTC
**Cost:** Zero (DB + artifact read)
**Source data:** Sprint 2 report `report_dfd5e69a3a42` + `demo_track2_20260526T040110Z/web_collection_audit.json`

### Key findings

- 27 accepted pricing_pressure URLs → only 3 produced facts
- CoreWeave/GCP zero-fact cause: JS-rendered price tables (HTML scraping cannot access)
- RunPod/Dell zero-fact cause: comparison blog articles, not direct pricing pages
- SemiAnalysis zero-fact cause: paywall/partial content

---

## Stale/Superseded Sprint 4 Folders

**Archived to:** `pipeline_audit_artifacts/archive_sprint4_stale/`

| Folder | Reason |
|---|---|
| `pricing_extraction_diagnosis_20260526T061051Z/` | Empty first run (DB schema bug) |
| `demo_track2_20260526T061824Z/` | Timeout killed during round 1 expansion |

---

## Sprint 3 Authoritative Artifacts (unchanged)

These remain intact and are NOT superseded by Sprint 4:

- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/` — Sprint 3 evidence quality audit
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/` — Sprint 2 authoritative 3-company demo run

---

## Files to Send for External Review

**Sprint 4 demo run:**
- `pipeline_audit_artifacts/demo_track2_20260526T063140Z/demo_report_summary.json`
- `pipeline_audit_artifacts/demo_track2_20260526T063140Z/quality_gate_audit.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T064101Z/pricing_pressure_semantics_audit.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T064101Z/evidence_quality_summary.json`

**Before/after comparison:**
- `SPRINT_4_BEFORE_AFTER_COMPARISON.md`
- `EVIDENCE_CLEANUP_SPRINT_4_REPORT.md`

**Code changes made this sprint:**
- `backend/app/utils/url_scorer.py` (COMPANY_IR_DOMAINS + IR-nav rejection)
- `backend/app/pipeline/node_validate_and_split.py` (metadata guard + pricing sanity, tuple return)
- `backend/app/pipeline/state.py` (validation_audit field)
- `backend/app/pipeline/graph.py` (unpack tuple, thread validation_audit)
- `backend/scripts/pricing_document_extraction_diagnosis.py` (new gap diagnosis script)
