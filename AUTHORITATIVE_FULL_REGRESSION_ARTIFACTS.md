# Authoritative Full Regression Artifacts

**Created:** 2026-05-26
**Regression outcome:** CONDITIONAL — clean regression attempt failed (Agent 1 P0 bug); Sprint 4 run used as authoritative baseline.

---

## Authoritative Report in DB

| Field | Value |
|---|---|
| `report_id` | `report_3dfb4b94068b` |
| `created_at` | 2026-05-26 06:40:04 |
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | `fact_count 43 < 50` |
| `pulse_score` | 57.0 |
| `evidence_count` | 43 |
| `source_count` | 17 |
| `covered_signal_types` | ALL 6 |

---

## Full Regression Folder

```
pipeline_audit_artifacts/full_regression_20260526T065737Z/
├── git_status_before.txt
├── git_status_after.txt
├── environment_readiness_redacted.json
├── command_manifest.json
├── backend_import_check.log
├── demo_pipeline_terminal.log        ← failed clean regression terminal log
├── evidence_quality_terminal.log
├── pricing_diagnosis_terminal.log
├── frontend_build.log                ← exit 0 (clean build)
└── review_bundle/
    ├── final_report_quality_summary.json
    ├── demo_report_summary.json
    ├── query_planner_audit.json
    ├── web_collection_audit.json
    ├── quality_gate_audit.json
    ├── fetch_error_summary.json
    ├── pipeline_run.log
    ├── demo_pipeline_terminal.log
    ├── evidence_quality_terminal.log
    ├── pricing_diagnosis_terminal.log
    ├── evidence_quality_summary.json
    ├── signal_semantics_audit.json
    ├── pricing_pressure_semantics_audit.json
    ├── suspicious_claims.json
    ├── source_tier_quality_audit.json
    └── pricing_extraction_gap_summary.json
```

**16 files in review_bundle.** This is the send-to-review package.

---

## Sprint 4 Demo Run (Authoritative Baseline)

```
pipeline_audit_artifacts/demo_track2_20260526T063140Z/
├── pipeline_run.log                  ← 436 lines, EXIT_CODE:0
├── demo_scope_config.json
├── query_planner_audit.json
├── web_collection_audit.json
├── quality_gate_audit.json
├── fetch_error_summary.json
├── final_report_quality_summary.json
└── demo_report_summary.json
```

**All 8 files present. COMPLETE.**

---

## Fresh Evidence Quality Audit

```
pipeline_audit_artifacts/evidence_quality_20260526T071826Z/
├── evidence_quality_summary.json
├── pricing_pressure_semantics_audit.json
├── signal_semantics_audit.json
├── suspicious_claims.json
├── source_tier_quality_audit.json
└── evidence_quality_run.log
```

Run against `report_3dfb4b94068b` immediately before regression. **All 6 files present. COMPLETE.**

---

## Fresh Pricing Gap Diagnosis

```
pipeline_audit_artifacts/pricing_extraction_diagnosis_20260526T071833Z/
├── pricing_document_extraction_diagnosis.json
├── cloud_pricing_docs_with_price_patterns.json
├── cloud_pricing_docs_without_price_patterns.json
└── pricing_extraction_gap_summary.json
```

Run against `report_3dfb4b94068b`. Key finding: 15/18 pricing URLs produced zero facts; CoreWeave/GCP inaccessible (JS-rendered). **All 4 files present. COMPLETE.**

---

## Historical Artifacts (Kept for Before/After)

| Folder | Sprint | Status |
|---|---|---|
| `demo_track2_20260526T040110Z/` | Sprint 2 | Authoritative Sprint 2 baseline |
| `pricing_pressure_20260526T033831Z/` | Sprint 2 | Sprint 2 pricing retrieval audit |
| `evidence_quality_20260526T053621Z/` | Sprint 3 | Sprint 3 evidence audit |
| `evidence_quality_20260526T064101Z/` | Sprint 4 | Sprint 4 evidence audit |
| `pricing_extraction_diagnosis_20260526T061730Z/` | Sprint 4 | Sprint 4 pricing diagnosis |

---

## Stale Artifacts Archived

| Archive Folder | Contents |
|---|---|
| `archive_sprint2_stale/` | 9 stale Sprint 2 runs |
| `archive_sprint4_stale/` | 2 incomplete Sprint 4 runs (timeout + DB schema bug) |
| `archive_before_full_regression_20260526T065615Z/` | 1 failed clean regression run (`demo_track2_20260526T071020Z`) — Agent 1 ValueError |

---

## What to Send for Review

The `review_bundle/` directory contains all 16 files needed for a complete external review:

- Pipeline audit: `query_planner_audit.json`, `web_collection_audit.json`, `quality_gate_audit.json`, `fetch_error_summary.json`
- Report output: `final_report_quality_summary.json`, `demo_report_summary.json`
- Evidence quality: `evidence_quality_summary.json`, `signal_semantics_audit.json`, `pricing_pressure_semantics_audit.json`, `suspicious_claims.json`, `source_tier_quality_audit.json`
- Pricing coverage: `pricing_extraction_gap_summary.json`
- Logs: `pipeline_run.log`, `demo_pipeline_terminal.log`, `evidence_quality_terminal.log`, `pricing_diagnosis_terminal.log`

**Send path:** `pipeline_audit_artifacts/full_regression_20260526T065737Z/review_bundle/`

---

## File Integrity Notes

- `backend/data/pulselens.db` — NOT TOUCHED. All 3 authoritative reports remain in DB.
- `backend/.env` — NOT TOUCHED.
- All markdown sprint reports — KEPT.
- Source code — NOT DELETED OR REVERTED. Sprint 4 fixes remain active.
