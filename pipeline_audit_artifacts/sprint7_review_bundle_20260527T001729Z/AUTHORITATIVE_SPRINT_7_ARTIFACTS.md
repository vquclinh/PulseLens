# Authoritative Sprint 7 Artifacts

**Date:** 2026-05-27
**Sprint 7 outcome:** SUCCESS — No rollback triggered.

---

## Authoritative Report

| Field | Value |
|---|---|
| report_id | `report_05aacb872fda` |
| quality_status | PARTIAL_PASS |
| quality_reason | fact_count 49 < 50 |
| pulse_score | 55.8 |
| pulse_status | stable |
| pulse_confidence | 0.732 |
| evidence_count | 49 |
| source_count | 23 URLs / 12 unique domains |
| companies_covered | AMD, Nvidia, Supermicro |
| all_core_signals_covered | yes (investor_signal, pricing_pressure, product_launch, supplier_risk) |
| optional_signals_covered | strategic_messaging |
| suspicious_claims | 0 |
| contradictions | 0 |
| avg_evidence_confidence | 0.931 |
| verified_claims | 8 |
| watch_list_items | 3 |

---

## Pipeline Artifact Directory

**Primary:** `pipeline_audit_artifacts/demo_track2_20260526T165950Z/`

| File | Contents |
|---|---|
| `query_planner_audit.json` | Per-round query telemetry, signal counts, caps, minimums, targeted regen |
| `web_collection_audit.json` | Per-query URL fetch results, zero-doc rates |
| `quality_gate_audit.json` | Round 0 and round 1 quality gate decisions |
| `fetch_error_summary.json` | Fetch error breakdown |
| `final_report_quality_summary.json` | Final quality gate state |
| `demo_report_summary.json` | Report metadata, signals, watch list |
| `demo_scope_config.json` | Scope configuration used |
| `pipeline_run.log` | Full pipeline stdout/stderr log |

---

## Evidence Quality Artifact Directory

**Primary:** `pipeline_audit_artifacts/evidence_quality_20260526T171620Z/`

| File | Contents |
|---|---|
| `evidence_quality_summary.json` | Top-level quality metrics (suspicious=0, avg_conf=0.931) |
| `signal_semantics_audit.json` | Per-signal suspicious/confidence breakdown |
| `pricing_pressure_semantics_audit.json` | Pricing signal strength classification |
| `source_tier_quality_audit.json` | Domain tier assessment (authoritative/acceptable/suspicious) |
| `suspicious_claims.json` | Suspicious claim list (empty — 0 claims) |
| `evidence_quality_run.log` | Audit stdout/stderr |

---

## Sprint 7 Review Bundle

**Primary:** `pipeline_audit_artifacts/sprint7_review_bundle_20260527T001729Z/`

Contains all files from both directories above, plus static test results.

---

## Static Test Artifact

**Primary:** `pipeline_audit_artifacts/sprint7_signal_balance_tests_20260526T165738Z/`

| Item | Value |
|---|---|
| results.json | All 15 tests passed |
| total_passed | 15 / 15 |
| all_passed | true |

---

## Code Changes (Sprint 7)

**Only file modified:** `backend/app/pipeline/agent1_query_planner.py`

Changes:
- **B1:** `_DEMO_SIGNAL_QUERY_MINIMUMS` dict (investor=4, product_launch=4, supplier_risk=3, strategic_messaging=2)
- **B1:** `_DEMO_SIGNAL_QUERY_CAPS` dict (investor_signal=7)
- **B2:** `_MULTIHYDE_SYSTEM` prompt: `{domain_rules_block}` and `{balance_rules_block}` placeholders with demo-scope signal-domain rules
- **B3:** `_trim_queries_to_limit` accepts `signal_caps` parameter, cap enforced in weighted fill step
- **B4 + Safety Fix 1:** `_enforce_final_quality` unconditional cap pass (runs even when total ≤ max_queries)
- **B4:** `_parse_and_validate_with_regeneration` and `run()` thread signal_caps and signal_minimums through call stack
- **B5 + Safety Fix 2:** `_targeted_signal_regeneration` method (max 2 calls, priority [product_launch, supplier_risk, strategic_messaging], blocking condition for strategic_messaging)
- **B6:** New telemetry fields in `last_query_telemetry`

**No other files modified.** LangGraph DAG, node order, Quality Gate thresholds, downstream agents, pricing_pressure_playbook, schema, and frontend unchanged.

---

## Document Index

| Document | Description |
|---|---|
| `AGENT1_SIGNAL_DISTRIBUTION_AUDIT_SPRINT_7.md` | Root cause analysis: Sprint 5 vs Sprint 6 Retry per-signal and per-domain breakdown |
| `SPRINT_7_IMPLEMENTATION_PLAN.md` | Implementation plan (B1–B6, Part C, D, E) |
| `FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md` | Stage-by-stage pipeline execution trace |
| `BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md` | Sprint 7 changes, telemetry, outcomes, static test summary |
| `SPRINT_7_REGRESSION_COMPARISON.md` | Sprint 4/5/6 Retry/7 side-by-side comparison |
| `AUTHORITATIVE_SPRINT_7_ARTIFACTS.md` | This file — artifact index and authoritative report fields |

---

## Sprint 5 Baseline (for reference)

| Field | Sprint 5 value |
|---|---|
| report_id | report_10f68adcaf0f |
| quality_status | PARTIAL_PASS |
| fact_count | 40 |
| source_count | 19 |
| pulse_score | 53.6 |
| suspicious_claims | 0 |
| product_launch | 14 |
| investor_signal | 13 |

Sprint 7 supersedes Sprint 5 as the authoritative passing run: 49 facts (vs 40), 23 sources (vs 19), pulse_score 55.8 (vs 53.6), 0 suspicious claims.

---

## Rollback Status

Sprint 7 rollback rule was evaluated:
- `fact_count < 40`: 49 ≥ 40 → PASS
- `suspicious_claim_count > 0`: 0 = 0 → PASS
- `product_launch < 8`: 19 ≥ 8 → PASS

**Rollback NOT triggered. `agent1_query_planner.py` Sprint 7 changes are retained.**

Git HEAD at Sprint 7 completion: Sprint 7 code (after `f8e8b4c fix bug in agent1 and agent4` base + Sprint 7 additions).
