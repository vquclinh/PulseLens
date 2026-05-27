# Sprint 5 Integrity Audit Plan

**Date:** 2026-05-26
**Auditor:** Claude Code (automated)
**Status:** Plan written before implementation (as required)

---

## Purpose

Verify that the Sprint 5 Agent 1 expansion fix is general-purpose and correct —
not hardcoded to pass the current demo, not bypassing validation, not hiding failures,
not lowering thresholds, and not introducing fake or misleading telemetry.

---

## Files to Inspect

| File | Why |
|---|---|
| `backend/app/pipeline/agent1_query_planner.py` | Only runtime file changed in Sprint 5 |
| `backend/scripts/test_agent1_expansion_stability.py` | New zero-cost test — assess quality |
| `backend/app/config/quality_gates.py` | Verify MIN_FACTS=50, MIN_SOURCE_COUNT=15 unchanged |
| `backend/app/pipeline/node_quality_gate.py` | Verify quality gate logic unchanged |
| `backend/app/pipeline/graph.py` | Verify LangGraph DAG unchanged |
| `backend/app/config/demo_scope.py` | Verify demo scope unchanged |
| `pipeline_audit_artifacts/sprint5_review_bundle_20260526T081013Z/query_planner_audit.json` | Verify live telemetry matches code claims |
| `pipeline_audit_artifacts/agent1_expansion_test_20260526T075733Z/agent1_expansion_test_results.json` | Verify test output |

---

## Audit Checklist

### 1. Hardcoding Risk Scan
Grep `agent1_query_planner.py` and related files for:
- Specific report IDs (`report_10f68`, `report_3dfb`)
- Company-name special-casing (`if company == "Nvidia"`, `if entity == "AMD"`)
- Forced-pass conditions (`force_pass`, `bypass_quality`, `skip_gate`, `FORCE`, `BYPASS`)
- Fake evidence flags

### 2. Agent 1 Fix Generality
Inspect all 4 fix sites to confirm they are controlled by runtime parameters, not constants:
- Fix 1 (`_trim_queries_to_limit`): does the required-first loop use only the passed-in
  `required_signal_types` set? No company or signal type literals?
- Fix 2 (`_enforce_final_quality`): is `is_expansion` a parameter, not a module-level switch?
- Fix 3 (`_parse_and_validate_with_regeneration`): pure pass-through?
- Fix 4 (`run()`): telemetry populated from runtime data only?

### 3. Telemetry Correctness
Verify naming accuracy of new telemetry fields:
- `expansion_generated_signal_counts` — does it reflect pre-trim LLM generation or post-trim final counts?
- `expansion_trimmed_signal_counts` — same question
- Are both fields computed from the same dict? (known issue to document)
- Does `expansion_unsatisfied_signals` accurately represent signals with zero coverage?
- Does `expansion_failure_recovered` only become `True` when the best-effort path fires?

**Pre-identified finding:** Both `expansion_generated_signal_counts` and
`expansion_trimmed_signal_counts` are set from the same `signal_counts` dict computed
AFTER `_parse_and_validate_with_regeneration` returns (post-trim). The "generated" name
implies pre-trim LLM output counts; the actual value is post-trim. Must document as naming
inaccuracy.

### 4. Test Quality Audit
Assess `test_agent1_expansion_stability.py` for:
- Coverage: does it test the two fix mechanisms (Fix 1 = trim order, Fix 2 = non-fatal path)?
- Generality: would tests pass for any companies, or are they implicitly locked to demo companies?
- Round 0 regression: does it verify that `is_expansion=False` still raises ValueError?
- False-positive risk: do tests assert the right things, or could they pass even if the fix regressed?

### 5. Static Hardcode Scan (all pipeline files)
Run grep across all `backend/app/pipeline/` and `backend/scripts/` for:
```
report_10f68 | report_3dfb | force_pass | bypass_quality | skip_gate | fake_evidence | HARDCODE
```
Distinguish Sprint 5 changes from pre-existing company references in other agents.

### 6. Threshold Audit
Read `backend/app/config/quality_gates.py`:
- Confirm `min_facts` default = 50 (QUALITY_MIN_FACTS)
- Confirm `min_source_count` default = 15 (QUALITY_MIN_SOURCE_COUNT)
- Confirm `node_quality_gate.py` uses `cfg.min_facts` and `cfg.min_source_count` (not overrides)
- Confirm `agent1_query_planner.py` was not granted any threshold bypass

### 7. LangGraph Architecture Audit
Confirm via `git diff`:
- `graph.py`: no changes (DAG topology, node order, conditional edges unchanged)
- `node_quality_gate.py`: no changes
- `demo_scope.py`: no changes

---

## Will Any Code Be Changed?

**Only if a critical issue is found.** Pre-identified issues:
- **Naming inaccuracy** (`expansion_generated_signal_counts`): Document in report; patch if user approves.
  This is a misleading name, not a functional bug.
- All other findings expected to be clean.

## Will Any Tests Be Run?

Optionally one randomized unit test (zero API cost) to verify `_trim_queries_to_limit`
generality beyond the fixed demo-company scenarios. This uses Python stdlib `random` only.

## Will Any Live API Calls Be Made?

**No.** No BrightData. No OpenRouter. No live pipeline run.

---

## Artifact Output

Folder: `pipeline_audit_artifacts/sprint5_integrity_audit_<timestamp>/`

Files to create:
- `SPRINT_5_INTEGRITY_AUDIT_REPORT.md` — root dir, executive summary + checklist results
- `SPRINT_5_HARDCODE_SCAN_RESULTS.md` — root dir, raw grep output + analysis
- `SPRINT_5_TEST_QUALITY_REVIEW.md` — root dir, test quality assessment

## Sprint 5 Artifacts: Not to Be Touched

The following Sprint 5 folders must NOT be deleted, moved, or archived during this audit:
- `pipeline_audit_artifacts/demo_track2_20260526T075840Z/`
- `pipeline_audit_artifacts/evidence_quality_20260526T080855Z/`
- `pipeline_audit_artifacts/agent1_expansion_test_20260526T075733Z/`
- `pipeline_audit_artifacts/sprint5_review_bundle_20260526T081013Z/`
- `pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/`
