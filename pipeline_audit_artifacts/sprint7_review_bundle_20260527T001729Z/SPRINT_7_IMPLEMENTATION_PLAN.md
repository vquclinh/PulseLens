# Sprint 7 Implementation Plan — Balanced Query Planning + Full Stage Regression Logging

**Date:** 2026-05-26
**Sprint 5 baseline:** `report_10f68adcaf0f` (PARTIAL_PASS, 40 facts, 19 sources)
**Sprint 6 Retry:** `report_a5a432182ba9` (PARTIAL_PASS, 34 facts, 9 sources — REGRESSED, reverted)
**Git HEAD:** `f8e8b4c fix bug in agent1 and agent4`

---

## 1. Repo State Confirmation

| Item | Status |
|---|---|
| Git HEAD | `f8e8b4c` — Sprint 5 baseline |
| Uncommitted changes | None |
| `agent1_query_planner.py` | Sprint 5 state — expansion fix only, no Sprint 6 Retry changes |
| `pricing_pressure_playbook.py` | Sprint 5 state — reverted |
| `agent3_fact_extractors.py` | Sprint 5 state — reverted |
| `quality_gates.py` | MIN_FACTS=50, MIN_SOURCE_COUNT=15 — unchanged |

---

## 2. Root Cause of Sprint 6 Retry Regression

**Primary:** `_MULTIHYDE_SYSTEM` prompt does not enforce source-domain specificity per signal type.
The LLM generated product_launch and supplier_risk queries that targeted `ir.amd.com` and `sec.gov`
— the same investor-focused domains. Agent 3 classified content from these pages as investor_signal
(financial data dominates the text), causing source diversity collapse (19→9 domains) and signal
collapse (product_launch 14→1, investor_signal 13→29).

**Secondary:** No cap on investor_signal LLM query generation. The LLM can legally fill all 17
LLM budget slots with investor_signal queries without violating any existing code constraint.

**Not caused by:** Pricing playbook changes, Agent 3 changes, or LangGraph topology.

---

## 3. Agent 1 Query Distribution Failure (Sprint 6 Retry)

| Source | Sprint 5 | Sprint 6 Retry |
|---|---|---|
| Total queries | 42 (32+10) | 32 (32+0) |
| investor_signal queries (LLM) | ~5-7 | ~12-15 |
| product_launch queries (LLM) | ≥3 (min met) | ≥3 (min met, wrong domains) |
| supplier_risk queries (LLM) | ≥2 (min met) | ≥2 (min met, wrong domains) |
| Source domains hit | 19 | 9 |
| investor_signal facts | 13 | 29 |
| product_launch facts | 14 | 1 |

The minimum count checks passed (no crash), but the source domains were homogeneous.

---

## 4. Files to Modify

| File | Change |
|---|---|
| `backend/app/pipeline/agent1_query_planner.py` | SOLE MODIFIED FILE — 6 targeted changes |

---

## 5. Architecture Impact

| Component | Changed? |
|---|---|
| LangGraph DAG | **NO** |
| Node order | **NO** |
| Quality Gate thresholds | **NO** (MIN_FACTS=50, MIN_SOURCE_COUNT=15) |
| Downstream agents (2-8) | **NO** |
| `pricing_pressure_playbook.py` | **NO** |
| `agent3_fact_extractors.py` | **NO** |
| `demo_scope.py` / `quality_gates.py` | **NO** |
| Schema / frontend | **NO** |
| Live API calls (BrightData/OpenRouter) | Only in Part E demo run |

---

## 6. Code Changes (Parts B1-B6 in `agent1_query_planner.py`)

### B1 — New constants (after line 86)
- `_DEMO_SIGNAL_QUERY_MINIMUMS`: stronger per-signal LLM minimums for demo scope
- `_DEMO_SIGNAL_QUERY_CAPS`: investor_signal cap=7 to prevent monopolization

### B2 — `_MULTIHYDE_SYSTEM` prompt update
- Add `SIGNAL-SPECIFIC SOURCE DOMAIN RULES` section: investor→SEC/IR, product_launch→newsroom/review sites, supplier_risk→reuters/bloomberg
- Add `SIGNAL BALANCE RULE` section: investor cap, product_launch min, supplier_risk min
- Variables `{investor_cap}`, `{product_min}`, `{supplier_min}` injected at call time

### B3 — `_trim_queries_to_limit` signature
- Add `signal_caps: dict[str, int] | None = None` parameter
- In weighted fill step: skip queries where signal is at cap

### B4 — Thread `signal_caps` through call chain
- `_enforce_final_quality`: add `signal_caps` parameter, pass to `_trim_queries_to_limit`
- `_parse_and_validate_with_regeneration`: add `signal_caps` parameter, pass to `_enforce_final_quality`
- `run()`: pass `signal_caps=_DEMO_SIGNAL_QUERY_CAPS` when `demo_scope=True`
- `run()`: use `_DEMO_SIGNAL_QUERY_MINIMUMS` (filtered to `required_signal_types`) instead of `_signal_minimums_for(...)` when `demo_scope=True and not is_expansion`

### B5 — `_targeted_signal_regeneration` method + call in `run()`
- New private method: calls LLM with single-signal focused prompt when a signal is below its demo minimum
- Called from `run()` after Phase 2+3 completes, before final enforcement
- Records `targeted_regeneration_attempts` and `targeted_regeneration_success_by_signal` telemetry

### B6 — New telemetry fields in `run()`
- `llm_generated_query_counts_by_signal`
- `deterministic_query_counts_by_signal`
- `final_query_counts_by_signal`
- `per_signal_minimums_used`
- `per_signal_caps_used`
- `query_distribution_before_trim`
- `query_distribution_after_trim`
- `signal_budget_violations`
- `targeted_regeneration_attempts`
- `targeted_regeneration_success_by_signal`

---

## 7. Cheap Tests (Part C)

File: `backend/scripts/test_agent1_signal_balance.py`
Output: `pipeline_audit_artifacts/sprint7_signal_balance_tests_<ts>/`
13 tests — zero API cost.

---

## 8. Live Pipeline Run (Part E)

ONE demo run after all tests pass:
```bash
python backend/scripts/demo_track2_ai_hardware_audit.py
python backend/scripts/evidence_quality_audit.py --report-id <new_id>
```

---

## 9. Rollback Strategy

Code change is in `agent1_query_planner.py` only. Revert with:
```bash
git checkout -- backend/app/pipeline/agent1_query_planner.py
```

Rollback triggers (automatic):
- fact_count < 40
- suspicious_claim_count > 0
- product_launch < 8

---

## 10. Expected Outcome

| Metric | Sprint 5 | Sprint 6 Retry | Sprint 7 Target |
|---|---|---|---|
| fact_count | 40 | 34 | 45-55 |
| investor_signal facts | 13 | 29 | 10-16 |
| product_launch facts | 14 | 1 | 10-16 |
| pricing_pressure facts | 5 | 1 | 5-9 |
| supplier_risk facts | 2 | 3 | 3-8 |
| source domains | 19 | 9 | 15-22 |
| suspicious_claims | 0 | 7 | 0 |
| quality_status | PARTIAL_PASS | PARTIAL_PASS | PASS / PARTIAL_PASS honest |
