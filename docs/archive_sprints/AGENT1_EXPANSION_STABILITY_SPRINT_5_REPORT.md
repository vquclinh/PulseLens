# Agent 1 Expansion Stability — Sprint 5 Report

**Date:** 2026-05-26
**Fixed by:** Sprint 5 (this session)
**Status:** P0 resolved — pipeline runs cleanly end-to-end

---

## 1. Files Changed

| File | Change |
|---|---|
| `backend/app/pipeline/agent1_query_planner.py` | 4 fixes (see §3) |
| `backend/scripts/test_agent1_expansion_stability.py` | NEW — zero-cost stability test |

No other files modified. LangGraph DAG, node order, state schema, quality thresholds, agents 2–7,
frontend, database: all unchanged.

---

## 2. Cleanup Performed

| Action | Detail |
|---|---|
| Archive created | `pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/` |
| Folders archived | `evidence_quality_20260526T064101Z/`, `pricing_extraction_diagnosis_20260526T061730Z/` |
| Cache deleted | 1798 `__pycache__/` dirs + 1 `.pytest_cache/` dir |
| Manifest | `CLEANUP_BEFORE_SPRINT5_MANIFEST.md` |

---

## 3. Root Cause

**Trigger:** Quality gate round 0 `FAIL_EXPAND` for `fact_count < 50` and/or `source_count < 15`
when ALL required signal types already covered → `low_signal_types = []` → expansion falls back
to targeting all 4 required types → `pricing_pressure ∈ required_signal_types` →
12 deterministic pricing playbook queries injected.

**Bug A — `_trim_queries_to_limit`:** Pricing playbook queries (`q_price_*`) were added first,
consuming all 10 expansion query slots before required signal types could be reserved.
When the loop tried to add investor_signal/product_launch/supplier_risk queries, the cap was
already full — those queries were silently dropped.

**Bug B — `_enforce_final_quality`:** After trimming, the missing signal type check raised
`ValueError` unconditionally (both expansion and normal rounds). The `for _attempt in range(2)`
retry loop exhausted both attempts → unhandled `raise` → LangGraph pipeline abort.

**Secondary cause:** Near-duplicate rejection in `_parse_candidates` eliminated non-pricing LLM
expansion queries that duplicated round 0 queries (which already covered investor/product/supplier
extensively). Only novel pricing queries survived, and those alone matched the 12 playbook queries.

---

## 4. Fix Implemented

### Fix 1 — `_trim_queries_to_limit` (line ~1025)
Swapped loop order: required signal types reserved **before** pricing playbook.

```python
# BEFORE: pricing playbook first (bug)
for query in queries:
    if query.query_id.startswith("q_price_"):
        add(query)
for signal_type in required_signal_types:   # ← cap already full, nothing added
    ...

# AFTER: required signal types first (fix)
for signal_type in required_signal_types:   # ← reserve 1 slot each
    ...
for query in queries:                        # ← pricing fills remaining cap
    if query.query_id.startswith("q_price_"):
        add(query)
```

### Fix 2 — `_enforce_final_quality` (line ~733)
Added `is_expansion: bool = False` parameter. When `is_expansion=True` and signals missing:
log warning, record `expansion_unsatisfied_signals` / `expansion_failure_recovered=True`,
return best-effort queries. Round 0 behavior unchanged — still raises ValueError.

### Fix 3 — `_parse_and_validate_with_regeneration` (line ~520)
Added `is_expansion: bool = False`; passed through to `_enforce_final_quality`.

### Fix 4 — `run()` (line ~394)
Passed `is_expansion=is_expansion` to `_parse_and_validate_with_regeneration`. Added expansion
telemetry to `self.last_query_telemetry`:

```
expansion_requested_missing_signals  — signal types targeted in expansion
expansion_generated_signal_counts    — per-type query counts after expansion
expansion_trimmed_signal_counts      — per-type counts after cap trim
expansion_unsatisfied_signals        — types with zero coverage after trim
expansion_failure_recovered          — True if best-effort fallback was used
query_cap_before_after               — max vs returned count
```

These flow into `query_planner_audit` state field (already `Dict`) and are saved in
`query_planner_audit.json` artifact.

---

## 5. Tests Run

### Zero-cost stability test (`test_agent1_expansion_stability.py`)

| Test | Scenario | Result |
|---|---|---|
| 1 | 12 pricing playbook + 0 non-pricing → expansion mode | **PASSED** — no crash; `expansion_failure_recovered=True` |
| 2 | 12 pricing playbook + 1 each of 3 non-pricing types → trim | **PASSED** — all required types preserved |
| 3 | Single missing type = pricing_pressure → playbook covers it | **PASSED** — clean pass, no unsatisfied |
| 4 | Round 0, is_expansion=False, missing types → must raise | **PASSED** — ValueError raised as expected |

All 4 tests passed. Verified before running demo pipeline.

### Backend import checks
All imports clean after fix: `agent1_query_planner`, `graph`, `node_quality_gate`,
`node_validate_and_split`, `state`, `test_agent1_expansion_stability`.

### Demo pipeline (`demo_track2_ai_hardware_audit.py`)
- Completed with EXIT_CODE:0
- Round 0 → FAIL_EXPAND → Round 1 expansion → PARTIAL_PASS
- Expansion telemetry: `expansion_unsatisfied_signals=[]`, `expansion_failure_recovered=False`
  (Fix 1 alone was sufficient — required signal types were available and preserved)

### Evidence quality audit
- 40 facts, 7 verified claims, 0 suspicious claims, 5 strong pricing (100%)
- Average confidence: 0.932

### Frontend build
- Exit 0, built in 3.79s

---

## 6. Demo Run Result

| Metric | Value |
|---|---|
| `report_id` | `report_10f68adcaf0f` |
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | `fact_count 40 < 50` |
| `pulse_score` | 53.6 |
| `pulse_status` | risk_rising |
| `evidence_count` | 40 |
| `source_count` | 19 |
| `zero_doc_query_rate` | 28.6% (12/42) |
| `fetch_error_rate` | 2.4% (1/42) |
| `covered_core_signals` | ALL 4 |
| `pricing_verdict` | ACCEPTABLE (5/5 strong) |
| `suspicious_claims` | 0 |
| `verified_claims` | 7 |
| `watch_list_items` | 4 |

---

## 7. Pipeline Stability

**Yes — pipeline can now run cleanly from scratch.**

The Agent 1 expansion ValueError is fully resolved. Both fix mechanisms are in place:
- Fix 1 (trim order) handles the common case where non-pricing expansion queries exist
- Fix 2 (non-fatal enforcement) handles the edge case where near-duplicate rejection leaves zero non-pricing queries

Round 0 validation is unchanged — strict, raises ValueError as before.
Quality Gate thresholds are unchanged — no threshold lowering.

---

## 8. Remaining Weaknesses (Inherited from Sprint 4)

| Priority | Weakness | Fix |
|---|---|---|
| P1 | `fact_count < 50` → PARTIAL_PASS | Retrieval depth: per-company pricing sub-queries, more source domains |
| P2 | CoreWeave/GCP pricing: 0 facts | Playwright headless-browser fallback for JS-rendered pages |
| P3 | `pricing_pressure` triangulation: 0 verified claims | Lower triangulation threshold for explicit-$ facts |
| P4 | 28.6% zero-doc query rate | Audit zero-doc queries; loosen site constraints |
| P5 | investor_signal distribution: now 32% (improved from 60%) | Continue diversifying query routing |

---

## 9. Next Recommended Sprint (Sprint 6)

1. Increase retrieval depth to consistently reach fact_count ≥50 (P1)
2. Playwright fallback for CoreWeave/GCP pricing pages (P2)
3. Pricing triangulation threshold: 1 independent source for explicit-$ facts (P3)
4. Full 8-company run ONLY after 3-company fact_count consistently ≥50
