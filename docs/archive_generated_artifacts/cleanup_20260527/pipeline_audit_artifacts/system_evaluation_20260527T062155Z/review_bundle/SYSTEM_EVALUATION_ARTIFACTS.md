# System Evaluation Artifacts

**Evaluation run:** 2026-05-27  
**Report ID:** `report_5760ae7b9861`

---

## Folder Paths

| Folder | Path |
|---|---|
| System evaluation | `pipeline_audit_artifacts/system_evaluation_20260527T062155Z/` |
| Demo pipeline run | `pipeline_audit_artifacts/demo_track2_20260527T062432Z/` |
| Evidence quality audit | `pipeline_audit_artifacts/evidence_quality_20260527T063557Z/` |
| Pricing diagnosis | `pipeline_audit_artifacts/pricing_extraction_diagnosis_20260527T063631Z/` |
| Review bundle | `pipeline_audit_artifacts/system_evaluation_20260527T062155Z/review_bundle/` |

---

## System Evaluation Folder (`system_evaluation_20260527T062155Z/`)

| File | Description |
|---|---|
| `00_git_status_before.txt` | Git status + log at evaluation start |
| `01_environment_readiness_redacted.json` | Env vars (set/missing only), thresholds, commit hash |
| `02_command_manifest.json` | All commands run, cost tier, expected outputs |
| `backend_import_check.log` | pipeline import check result |
| `fastapi_import_check.log` | FastAPI import check result |
| `agent1_expansion_stability_test.log` | Sprint 5 guard: 4/4 passed |
| `agent1_signal_balance_test.log` | Sprint 7 guard: 15/15 passed |
| `frontend_build.log` | npm build result (exit 0) |
| `static_safety_scan.json` | Safety scan results (all CLEAN) |
| `static_safety_scan.md` | Human-readable safety scan summary |
| `live_pipeline_terminal.log` | Full stdout+stderr of demo pipeline run |
| `evidence_quality_terminal.log` | Evidence quality audit output |
| `pricing_diagnosis_terminal.log` | Pricing diagnosis output |
| `SYSTEM_EVALUATION_REPORT.md` | Final report (31 questions answered) |
| `SYSTEM_EVALUATION_ARTIFACTS.md` | This file |
| `review_bundle/` | Curated subset for ChatGPT review |

---

## Demo Pipeline Folder (`demo_track2_20260527T062432Z/`)

| File | Description |
|---|---|
| `pipeline_run.log` | Full pipeline log |
| `demo_scope_config.json` | Scope: Nvidia/AMD/Supermicro, 4 core signals |
| `query_planner_audit.json` | Agent 1 telemetry: 42 queries, signal distribution, caps |
| `web_collection_audit.json` | Agent 2: 57 docs, 19 sources, zero-doc rates |
| `quality_gate_audit.json` | PARTIAL_PASS: fact_count 41 < 50 |
| `fetch_error_summary.json` | Fetch error breakdown |
| `final_report_quality_summary.json` | Full report JSON (quality + watch list + top signals) |
| `demo_report_summary.json` | Signal/company coverage summary |

---

## Evidence Quality Folder (`evidence_quality_20260527T063557Z/`)

| File | Description |
|---|---|
| `evidence_quality_summary.json` | 41 facts, 12 claims, avg_conf=0.924, 0 suspicious |
| `signal_semantics_audit.json` | Per-signal fact counts, confidence, suspicious flags |
| `pricing_pressure_semantics_audit.json` | 4 pricing facts: 1 strong, 3 insufficient_evidence |
| `suspicious_claims.json` | Empty — 0 suspicious claims found |
| `source_tier_quality_audit.json` | 11 domains: 3 authoritative, 6 acceptable, 2 unknown |
| `evidence_quality_run.log` | Full audit log |

---

## Pricing Diagnosis Folder (`pricing_extraction_diagnosis_20260527T063631Z/`)

| File | Description |
|---|---|
| `pricing_extraction_gap_summary.json` | 27 accepted pricing URLs, 3 produced facts, 25 zero-fact |
| `pricing_document_extraction_diagnosis.json` | Per-URL classification + gap cause |
| `cloud_pricing_docs_with_price_patterns.json` | URLs that did produce pricing facts |
| `cloud_pricing_docs_without_price_patterns.json` | URLs that yielded 0 facts |

---

## Review Bundle (`system_evaluation_20260527T062155Z/review_bundle/`)

28 files total. Priority order for ChatGPT review:

### Priority 1 — Send first
1. `SYSTEM_EVALUATION_REPORT.md`
2. `01_environment_readiness_redacted.json`
3. `final_report_quality_summary.json`
4. `quality_gate_audit.json`

### Priority 2 — Evidence audit
5. `evidence_quality_summary.json`
6. `suspicious_claims.json`
7. `signal_semantics_audit.json`
8. `source_tier_quality_audit.json`

### Priority 3 — Pricing gap
9. `pricing_extraction_gap_summary.json`
10. `pricing_pressure_semantics_audit.json`

### Priority 4 — Agent telemetry
11. `query_planner_audit.json`
12. `web_collection_audit.json`
13. `demo_report_summary.json`

### Priority 5 — Safety + tests
14. `static_safety_scan.json`
15. `agent1_signal_balance_test.log`

### Do NOT send (too large / raw)
- `live_pipeline_terminal.log` (95 kB)
- `pipeline_run.log` (93 kB)
- `web_collection_audit.json` (65 kB) — send only if debugging collection
- `pricing_document_extraction_diagnosis.json` (14 kB) — send only if debugging pricing
