# Sprint 5 Integrity Audit Report

**Date:** 2026-05-26
**Auditor:** Claude Code
**Artifact folder:** `pipeline_audit_artifacts/sprint5_integrity_audit_20260526T090117Z/`

---

## Executive Summary

The Sprint 5 Agent 1 expansion fix is **generally correct and safe**. No hardcoded report IDs,
no company-specific bypass logic, no threshold lowering, no LangGraph changes, no fake telemetry.
One **naming inaccuracy** in telemetry (two fields report identical post-trim data under different
names) is the only must-document finding. It is not a functional bug.

---

## Checklist Results

### 1. Hardcoding Risk — CLEAN

**Tested:** grep for `report_10f68`, `report_3dfb`, `force_pass`, `bypass_quality`, `skip_gate`,
`fake_evidence`, `HARDCODE`, `BYPASS`, `SKIP_QUALITY`, `FORCE_PASS` across
`agent1_query_planner.py` and `test_agent1_expansion_stability.py`.

**Result:** Zero matches. No hardcoded report IDs. No bypass conditions. No forced-pass logic.

Company references found in `agent1_query_planner.py`:
- Line 235–236: `PRIORITY_COMPANIES = ["Nvidia", "AMD", "Intel", "Dell", "HPE", "Micron"]` — 
  pre-existing constant (not a Sprint 5 change). Used to gate `require_priority_investor_signals`
  behavior, not to special-case expansion.
- Lines 235–240 in docstring examples: Nvidia/AMD in example query strings — docs only.

**No company-specific runtime branches introduced by Sprint 5.**

---

### 2. Agent 1 Fix Generality — PASS

**Fix 1 — `_trim_queries_to_limit` (line ~1059):**

```python
for signal_type in required_signal_types:      # ← uses runtime parameter
    if any(q.signal_type.value == signal_type for q in selected):
        continue
    for query in queries:
        if query.signal_type.value == signal_type:
            add(query)
            break
for query in queries:
    if query.query_id.startswith("q_price_"):  # ← prefix check, not company-specific
        add(query)
```

`required_signal_types` is a `set[str]` parameter computed from `scope.core_signal_types`
at runtime in `run()`. It is NOT hardcoded to the demo signal set. For a full 8-company run,
`required_signal_types` would include whatever signal types that scope configures.
`q_price_` prefix is a stable query-ID convention, not company-specific.

**Fix 2 — `_enforce_final_quality` (line ~795):**

`is_expansion: bool = False` is a boolean parameter. The non-fatal path fires only when
`is_expansion=True` AND signals are missing. Round 0 (`is_expansion=False`) still raises
`ValueError` unconditionally. Confirmed by Test 4 in the expansion stability test.

**Fix 3 — `_parse_and_validate_with_regeneration`:** Pure parameter pass-through. No logic added.

**Fix 4 — `run()` expansion telemetry block:** Computes signal counts from the actual
returned `queries` list. Uses `signal_counts.get(st, 0)` for keys in `required_signal_types`.
No hardcoded signal type names.

**Randomized generality test:** 100 trials with random company names (`CompA`, `CompB`, `CompC`),
random pricing playbook counts (0–15), random non-pricing query counts (0–4 per type). Result:
100/100 PASS. `_trim_queries_to_limit` preserves required signal types in all trials. Cap
invariant (≤10) holds in all trials.

---

### 3. Telemetry Correctness — ONE NAMING INACCURACY

Live telemetry from Sprint 5 demo run (`query_planner_audit.json`):

```json
"expansion_generated_signal_counts": {"pricing_pressure": 7, "product_launch": 1, "supplier_risk": 1, "investor_signal": 1},
"expansion_trimmed_signal_counts":   {"pricing_pressure": 7, "product_launch": 1, "supplier_risk": 1, "investor_signal": 1},
"query_cap_before_after": {"max_expansion_queries": 10, "queries_returned": 10}
```

**Finding:** Both fields are **identical dicts**. Both sum to 10 = `queries_returned`.

**Root cause:** Both are computed from the same `signal_counts` dict at lines 482–489 of `run()`,
AFTER `_parse_and_validate_with_regeneration` returns. That function internally calls
`_trim_queries_to_limit`, so the returned `queries` object is already post-trim. There is no
pre-trim count captured.

**Correct label:** `expansion_generated_signal_counts` should be named
`expansion_final_signal_counts` or `expansion_posttrim_signal_counts`. The "generated" name
implies pre-trim LLM output counts, which are not captured.

**Severity:** LOW — this is a **documentation/naming** issue, not a functional bug. The
Quality Gate downstream reads facts from documents, not from Agent 1 telemetry. No downstream
decision is wrong because of this label. The field still provides useful information (final
per-signal query distribution after the expansion round).

**Recommendation:** Rename `expansion_generated_signal_counts` → `expansion_final_signal_counts`
in a future sprint. Do not patch now as it would change the JSON schema visible in Sprint 5
review bundle artifacts.

Other telemetry fields:
- `expansion_unsatisfied_signals`: Correctly populated by `_enforce_final_quality` when
  best-effort path fires; correctly `[]` in both live run and Test 3. ✓
- `expansion_failure_recovered`: `False` in live run (Fix 1 alone was sufficient);
  `True` in Test 1 (best-effort path triggered). ✓
- `expansion_requested_missing_signals`: Populated from `expansion_signal_types or required_signal_types`
  at call time — correct. ✓
- `query_cap_before_after`: `queries_returned` is `len(queries)` post-trim. Accurate. ✓

---

### 4. Test Quality — ACCEPTABLE WITH MINOR GAP

**Coverage:**
- Test 1 tests Fix 2 (non-fatal best-effort path in `_enforce_final_quality`)
- Test 2 tests Fix 1 (`_trim_queries_to_limit` required-first order)
- Test 3 tests the happy-path (pricing_pressure alone as missing type → playbook covers it)
- Test 4 tests regression guard (round 0 `is_expansion=False` still raises ValueError)

Both fix mechanisms are directly tested. No tests that only validate output format without
checking the behavioral invariant.

**Generality concern:** `DEMO_COMPANIES = ["Nvidia", "AMD", "Supermicro"]` is hardcoded in the
test file. This mirrors the demo scope. The underlying functions (`_trim_queries_to_limit`,
`_enforce_final_quality`) do not have any knowledge of specific companies — they take
`expected_companies` as a parameter. Tests would produce equivalent results with any company
list. This is fixture data, not a runtime constraint.

**Gap — no test for Fix 1 + Fix 2 interaction (edge case):** The combined scenario where
Fix 1 preserves some required types but not all (partial coverage) is not directly tested.
Test 1 covers the "Fix 1 fails to help → Fix 2 fires" extreme. Test 2 covers "Fix 1 fully
works." The middle case (Fix 1 partially works, Fix 2 fires) is implicit but not explicit.
Acceptable for Sprint 5; worth adding in Sprint 6.

**False positive risk:** Low. Test 1 asserts `expansion_failure_recovered is True` and checks
`expansion_unsatisfied_signals` exactly. Test 2 asserts all 4 required signal types present
by name. Test 4 asserts ValueError is raised. These would catch regressions.

---

### 5. Static Hardcode Scan — CLEAN

Full results in `SPRINT_5_HARDCODE_SCAN_RESULTS.md`. Summary:
- No report-ID literals in any pipeline file
- No `force_pass`, `bypass_quality`, `skip_gate` patterns anywhere
- Company name references in other agents (`agent2_web_workers.py`, `agent4_finbert_scorer.py`,
  `agent5_contradiction_writer.py`, `pricing_pressure_playbook.py`) are pre-existing, not Sprint 5 changes.
  These are in internal test fixtures or AMD/Nvidia-specific playbook logic that was already
  present before Sprint 5.
- `agent1_query_planner.py` Sprint 5 diff: zero company literals added.

---

### 6. Threshold Audit — UNCHANGED

`backend/app/config/quality_gates.py`:
```python
min_facts: int = _env_int("QUALITY_MIN_FACTS", 50)          # default = 50 ← unchanged
min_source_count: int = _env_int("QUALITY_MIN_SOURCE_COUNT", 15)  # default = 15 ← unchanged
```

`backend/app/pipeline/node_quality_gate.py`:
```python
if len(facts) < cfg.min_facts:                              # uses config, no override
if source_count < cfg.min_source_count:                     # uses config, no override
```

`agent1_query_planner.py` Sprint 5 changes: no threshold references modified.

The `_enforce_final_quality` non-fatal path (Fix 2) does NOT lower the quality gate — it returns
best-effort queries from Agent 1 and lets the Quality Gate in `node_quality_gate.py` decide
PASS/FAIL_EXPAND/PARTIAL_PASS based on actual evidence facts. These are separate systems.
Agent 1's signal coverage check is a pre-condition for the query plan; it does not affect
the Quality Gate's fact-count or source-count decisions.

---

### 7. LangGraph Architecture — UNCHANGED

| File | Sprint 5 changes? |
|---|---|
| `backend/app/pipeline/graph.py` | NO (git diff: empty) |
| `backend/app/pipeline/node_quality_gate.py` | NO (git diff: empty) |
| `backend/app/config/demo_scope.py` | NO (git diff: empty) |

DAG topology, node order, conditional edges, `quality_gate_router`, `MemorySaver`
checkpointer — all unchanged.

---

## Must-Fix Issues

| # | Issue | Severity | Sprint |
|---|---|---|---|
| 1 | `expansion_generated_signal_counts` naming inaccuracy — both it and `expansion_trimmed_signal_counts` reflect post-trim counts; "generated" implies pre-trim | LOW | Sprint 6 |

## No Issues (Clean)

- No hardcoded report IDs or bypass logic
- Fix 1 and Fix 2 are generic (runtime-parameterized)
- LangGraph unchanged
- Quality Gate thresholds unchanged
- Round 0 validation still strict (confirmed by Test 4)
- 100/100 randomized trials pass

---

## Artifact Integrity

Sprint 5 artifacts inspected, not touched:
- `pipeline_audit_artifacts/demo_track2_20260526T075840Z/` — intact
- `pipeline_audit_artifacts/evidence_quality_20260526T080855Z/` — intact
- `pipeline_audit_artifacts/agent1_expansion_test_20260526T075733Z/` — intact
- `pipeline_audit_artifacts/sprint5_review_bundle_20260526T081013Z/` — intact
- `pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/` — intact
