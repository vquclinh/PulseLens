# Authoritative Sprint 5 Artifacts

**Created:** 2026-05-26
**Sprint 5 outcome:** COMPLETE — Agent 1 P0 fixed, fresh demo regression successful

---

## Authoritative Report in DB

| Field | Value |
|---|---|
| `report_id` | `report_10f68adcaf0f` |
| `created_at` | 2026-05-26 ~15:07 UTC |
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | `fact_count 40 < 50` |
| `pulse_score` | 53.6 |
| `evidence_count` | 40 |
| `source_count` | 19 |
| `covered_signal_types` | investor_signal, pricing_pressure, product_launch, strategic_messaging, supplier_risk |

---

## Cleanup Archive

```
pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/
├── evidence_quality_20260526T064101Z/      ← Sprint 4 version (superseded)
└── pricing_extraction_diagnosis_20260526T061730Z/  ← Sprint 4 version (superseded)
```

---

## Agent 1 Expansion Test

```
pipeline_audit_artifacts/agent1_expansion_test_20260526T075733Z/
├── agent1_expansion_test_results.json    ← all 4 tests PASSED
└── agent1_expansion_test.log
```

---

## Sprint 5 Demo Run

```
pipeline_audit_artifacts/demo_track2_20260526T075840Z/
├── pipeline_run.log                      ← EXIT_CODE:0, expansion round completed
├── demo_scope_config.json
├── query_planner_audit.json              ← expansion_unsatisfied_signals=[], recovered=False
├── web_collection_audit.json             ← 54 docs accepted
├── quality_gate_audit.json               ← PARTIAL_PASS, fact_count 40 < 50
├── fetch_error_summary.json              ← 1 fetch error
├── final_report_quality_summary.json     ← report_10f68adcaf0f
└── demo_report_summary.json
```

**All 8 expected files present. COMPLETE.**

---

## Sprint 5 Evidence Quality Audit

```
pipeline_audit_artifacts/evidence_quality_20260526T080855Z/
├── evidence_quality_summary.json         ← 40 facts, 7 verified, 0 suspicious
├── pricing_pressure_semantics_audit.json ← 5 strong, 0 weak, 0 misclassified
├── signal_semantics_audit.json
├── suspicious_claims.json                ← count=0
├── source_tier_quality_audit.json
└── evidence_quality_run.log
```

**All 6 expected files present. COMPLETE.**

---

## Sprint 5 Review Bundle (Send for External Review)

```
pipeline_audit_artifacts/sprint5_review_bundle_20260526T081013Z/
├── final_report_quality_summary.json
├── demo_report_summary.json
├── query_planner_audit.json
├── web_collection_audit.json
├── quality_gate_audit.json
├── fetch_error_summary.json
├── pipeline_run.log
├── evidence_quality_summary.json
├── signal_semantics_audit.json
├── pricing_pressure_semantics_audit.json
├── suspicious_claims.json
├── source_tier_quality_audit.json
├── agent1_expansion_test_results.json
├── agent1_expansion_test.log
├── backend_import_check.log
└── frontend_build.log
```

**16 files. This is the send-to-review package.**

---

## Historical Baselines (Retained)

| Folder | Sprint | Status |
|---|---|---|
| `demo_track2_20260526T040110Z/` | Sprint 2 | Authoritative Sprint 2 baseline |
| `demo_track2_20260526T063140Z/` | Sprint 4 | Sprint 4 authoritative demo run |
| `evidence_quality_20260526T053621Z/` | Sprint 3 | Sprint 3 evidence audit |
| `evidence_quality_20260526T071826Z/` | Sprint 4→5 transition | Pre-regression fresh audit |
| `full_regression_20260526T065737Z/` | Sprint 4→5 transition | Full regression folder + review bundle |
| `pricing_extraction_diagnosis_20260526T071833Z/` | Sprint 4→5 transition | Pre-regression diagnosis |
| `pricing_pressure_20260526T033831Z/` | Sprint 2 | Sprint 2 pricing audit |

---

## Stale Folders Archived

| Archive Folder | Contents |
|---|---|
| `archive_sprint2_stale/` | 9 stale Sprint 2 runs |
| `archive_sprint4_stale/` | 2 stale Sprint 4 runs |
| `archive_before_full_regression_20260526T065615Z/` | Failed clean regression run (Agent 1 P0 crash) |
| `archive_before_sprint5_20260526T075113Z/` | 2 superseded Sprint 4 audit folders |

---

## Files to Send to ChatGPT for Review

Path: `pipeline_audit_artifacts/sprint5_review_bundle_20260526T081013Z/`

Priority files:
1. `final_report_quality_summary.json` — report quality + pulse score
2. `query_planner_audit.json` — expansion telemetry (confirms fix)
3. `agent1_expansion_test_results.json` — test evidence
4. `evidence_quality_summary.json` — evidence quality metrics
5. `pricing_pressure_semantics_audit.json` — pricing verdict
6. `suspicious_claims.json` — clean (0 suspicious)
7. `quality_gate_audit.json` — gate result

---

## Integrity Notes

- `backend/data/pulselens.db` — NOT TOUCHED. All reports remain in DB.
- `backend/.env` — NOT TOUCHED.
- All markdown sprint reports — KEPT.
- Source code — NOT DELETED OR REVERTED. Sprint 4 + Sprint 5 fixes active.
- Only file modified in Sprint 5: `backend/app/pipeline/agent1_query_planner.py`
