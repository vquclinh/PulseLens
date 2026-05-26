# Sprint 5 Test Quality Review

**Date:** 2026-05-26
**Test file:** `backend/scripts/test_agent1_expansion_stability.py`
**Functions under test:** `_trim_queries_to_limit`, `QueryPlanner._enforce_final_quality`

---

## Coverage Summary

| Test | Fix Covered | Scenario | Pass/Fail |
|---|---|---|---|
| Test 1 | Fix 2 (non-fatal best-effort) | 12 pricing-only → no crash in expansion | PASSED |
| Test 2 | Fix 1 (required-first trim order) | 12 pricing + 1 each non-pricing → all types preserved | PASSED |
| Test 3 | Fix 1 + happy path | Single missing type = pricing_pressure → playbook covers it | PASSED |
| Test 4 | Round 0 regression | `is_expansion=False` + missing types → must raise ValueError | PASSED |

Both core fix mechanisms (Fix 1 and Fix 2) are directly exercised.

---

## Assertion Quality

### Test 1
- Asserts `expansion_failure_recovered is True` — catches if Fix 2 doesn't fire
- Asserts `expansion_unsatisfied_signals == {"investor_signal", "product_launch", "supplier_risk"}` — catches if telemetry is wrong
- Asserts no ValueError raised — catches if Fix 2 regressed to raising

If Fix 2 were reverted, Test 1 would fail with `ValueError`. Strong regression guard.

### Test 2
- Asserts all 4 required signal types are present in trimmed output
- Asserts `len(trimmed) <= MAX_EXPANSION_QUERIES`
- If Fix 1 were reverted (pricing first), pricing would fill all 10 slots → investor/product/supplier missing → Test 2 would fail. Strong regression guard.

### Test 3
- Asserts no missing types in output
- Asserts no ValueError raised
- Covers the path where pricing_pressure is the sole missing type and playbook queries provide coverage. Validates that Fix 1 does not displace pricing_pressure when it is a required type.

### Test 4
- Asserts ValueError IS raised for `is_expansion=False`
- Catches the risk of accidentally making round 0 non-fatal. Strong guard.

---

## Gaps

### Gap 1 — No partial-coverage interaction test

Scenario: Fix 1 preserves some required types but not all (e.g., cap=10, 3 non-pricing + 12 pricing
→ Fix 1 saves 3 types, but the 4th has no candidate query → Fix 2 fires). This is an intermediate
state not directly tested. Test 1 covers the extreme (all non-pricing absent); Test 2 covers full
success. The middle is implicit.

**Risk:** Low. Fix 1 and Fix 2 are independent. Fix 2's trigger condition (`missing_signals ≠ ∅`)
is the same regardless of how many types are missing. The combined behavior is validated by the
100-trial randomized test.

### Gap 2 — Tests use demo company names

`DEMO_COMPANIES = ["Nvidia", "AMD", "Supermicro"]` is hardcoded in the test file. Functions under
test take `expected_companies` as a runtime parameter; they do not use company names for logic.

**Risk:** Negligible. The randomized test (100 trials, `["CompA", "CompB", "CompC"]`) confirms
Fix 1 is company-name agnostic. The demo company names in the test are fixture data only.

### Gap 3 — No test for `expansion_generated_signal_counts` vs `expansion_trimmed_signal_counts` distinction

The tests do not check that these two fields differ (because they currently don't — both are
post-trim). If pre-trim counts were ever captured separately, there would be no test to verify
the distinction. This is related to the naming inaccuracy finding.

---

## Randomized Generality Test Results

100 trials, `random.seed(42)`, companies = `["CompA", "CompB", "CompC"]`, random mix of:
- 0–15 pricing playbook queries
- 0–4 each of `investor_signal`, `product_launch`, `supplier_risk`
- 0–5 additional `strategic_messaging` / `hiring_momentum` queries

**Invariant checked:** If a required signal type is available in input AND capacity is not
fully consumed by other required types, it must appear in output.

**Cap invariant:** `len(trimmed) <= 10`

**Result: 100/100 PASS.** Fix 1 is general-purpose.

---

## Overall Assessment

**ACCEPTABLE** — both fix mechanisms are tested and regression-guarded. The test would catch
a revert of Fix 1 (Test 2 fails) or Fix 2 (Test 1 fails). Round 0 safety is confirmed (Test 4).

Recommended additions for Sprint 6:
1. Test for partial Fix 1 + Fix 2 interaction (3 of 4 required types available in input)
2. Rename `expansion_generated_signal_counts` to `expansion_final_signal_counts` and add assertion
   that it equals post-trim counts
3. Parametrize tests with non-demo company names to make generality explicit
