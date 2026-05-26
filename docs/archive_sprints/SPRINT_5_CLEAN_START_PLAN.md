# Sprint 5 Clean Start Plan

**Created:** 2026-05-26
**Baseline report:** `report_3dfb4b94068b` (PARTIAL_PASS, pulse_score=57.0, 43 facts, 17 sources)
**Goal:** Fix P0 Agent 1 expansion crash, run fresh demo regression, produce clean Sprint 5 artifact set.

---

## 1. Root Cause — Agent 1 Expansion ValueError

**Error:** `ValueError: Quality gate FAIL: missing required signal types. Missing: ['investor_signal', 'product_launch', 'supplier_risk']`

**Crash path (confirmed from failed regression log `demo_track2_20260526T071020Z/pipeline_run.log`):**

1. Round 0 quality gate → `FAIL_EXPAND` for `fact_count 26 < 50`, `source_count 14 < 15`.
   All 4 required signal types already covered → `low_signal_types = []` (empty).

2. Expansion round 1:
   - `low_signal_types=None` (empty list → `None` via `or None` in graph.py)
   - `expansion_signal_types = []` (no missing types)
   - Fallback: `signal_types = requested_signal_types` (all 4 core demo types)
   - `required_signal_types = {'investor_signal', 'product_launch', 'pricing_pressure', 'supplier_risk'}`
   - `pricing_pressure in required_signal_types` → **12 pricing playbook queries injected**

3. LLM generates expansion queries; 43% rejection rate triggers replacement batch.
   Non-pricing LLM queries rejected as near-duplicates of round 0 queries.
   Accepted queries: mostly pricing_pressure.

4. After merge: ~12 pricing playbook + ~6 LLM (mostly pricing) = ~18 total.
   `_trim_queries_to_limit` called with `max_queries=10` (MAX_EXPANSION_QUERIES).

5. **Bug:** `_trim_queries_to_limit` adds `q_price_*` queries **first**, consuming all 10 slots.
   Required signal type loop finds cap full → no slots for investor/product/supplier.
   Result: 10 queries, all pricing_pressure.

6. `_enforce_final_quality` finds missing: `{'investor_signal', 'product_launch', 'supplier_risk'}` → raises `ValueError`.

7. Both `for _attempt in range(2)` attempts raise → unhandled → pipeline abort.

**Why Sprint 4 run succeeded:** Round 0 had 1 required type missing; expansion targeted only that
1 type; pricing playbook not injected (or cap not exceeded); LLM covered the gap.

---

## 2. Files to Archive

**Archive folder:** `pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/`

| Folder | Reason |
|---|---|
| `evidence_quality_20260526T064101Z/` | Sprint 4 version; superseded by 071826Z |
| `pricing_extraction_diagnosis_20260526T061730Z/` | Sprint 4 version; superseded by 071833Z |

---

## 3. Files to Keep

| Folder | Reason |
|---|---|
| `demo_track2_20260526T040110Z/` | Sprint 2 baseline |
| `demo_track2_20260526T063140Z/` | Sprint 4 authoritative demo run |
| `evidence_quality_20260526T053621Z/` | Sprint 3 audit (historical) |
| `evidence_quality_20260526T071826Z/` | Pre-regression fresh audit — Sprint 5 baseline |
| `full_regression_20260526T065737Z/` | Full regression folder + review bundle |
| `pricing_extraction_diagnosis_20260526T071833Z/` | Pre-regression diagnosis — Sprint 5 baseline |
| `pricing_pressure_20260526T033831Z/` | Sprint 2 pricing audit |
| `archive_*` folders | Existing stale archives |
| `backend/data/pulselens.db` | Database — never touch |
| `backend/.env` | Secrets — never touch |
| All `*.md` sprint reports | Documentation |
| All source code | Never delete |

---

## 4. Safe to Delete (Cache Only)

- `backend/**/__pycache__/` directories
- `backend/.pytest_cache/` if present

---

## 5. Files to Modify

**Only one source file:** `backend/app/pipeline/agent1_query_planner.py`

### Fix 1 — `_trim_queries_to_limit` (line ~1025)
Swap loop order: required signal types BEFORE `q_price_*` playbook queries.
Each required signal type gets its reserved slot before pricing fills remaining cap.

### Fix 2 — `_enforce_final_quality` (line ~733)
Add `is_expansion: bool = False`. When `is_expansion=True` and signals missing:
log warning, record `expansion_unsatisfied_signals`/`expansion_failure_recovered=True`,
return best-effort queries. Round 0 still raises ValueError as before.

### Fix 3 — `_parse_and_validate_with_regeneration` (line ~520)
Add `is_expansion: bool = False`; pass through to `_enforce_final_quality`.

### Fix 4 — `run()` (line ~394)
Pass `is_expansion=is_expansion` to `_parse_and_validate_with_regeneration`.
Add expansion telemetry to `self.last_query_telemetry`.

---

## 6. Architecture Impact — All NO

LangGraph DAG, node order, conditional routing, agents 2–7, state schema, quality thresholds,
frontend, DB, demo_scope.py: **unchanged**.

---

## 7. Run Order

```
1. Backend import checks (zero cost)
2. Agent 1 expansion stability test (zero cost) — STOP if fails
3. Demo pipeline (BrightData + OpenRouter)
4. Evidence quality audit (zero cost)
5. Frontend build (zero cost)
```

---

## 8. Rollback Strategy

- Archive only, no permanent deletions
- `agent1_query_planner.py` only file changed; `git stash` reverts
- Sprint 4 artifacts untouched; `report_3dfb4b94068b` remains in DB
- One failed demo run → stop and document
- PARTIAL_PASS → acceptable and honest; thresholds not lowered
