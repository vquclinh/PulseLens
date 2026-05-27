# Source Hygiene Audit Report

**Date:** 2026-05-27
**Pass 1 scope:** backend/app/, backend/scripts/ — classification of print(), TODO, hardcoded IDs, misplaced test files
**Pass 2 scope:** backend/scripts/ and backend/tests/ — structural reorganization of scripts into primary/diagnostics/archive/tests
**Audit type:** Read-only scan + path updates. No pipeline execution. No API calls.

---

## Pass 1 Audit Findings (backend/app/ and backend/scripts/)

| File | Finding | Classification | Action |
|---|---|---|---|
| `backend/app/pipeline/test_a2_a3.py` | Test file inside production app/ package; 70+ print() statements; hardcoded `/tmp/test_a2_a3` path | SHOULD MOVE | Moved to `backend/scripts/test_a2_a3.py` (Pass 1), then to `backend/scripts/archive_pre_submission/` (Pass 2) |
| `backend/scripts/evidence_quality_audit.py` L49-50 | `DEFAULT_REPORT_ID = "report_dfd5e69a3a42"` — stale Sprint 5/6 report ID | STALE DEFAULT | Updated to Sprint 7 report_id `report_05aacb872fda` |
| `backend/scripts/pricing_document_extraction_diagnosis.py` L46-47 | `_DEFAULT_REPORT_ID = "report_dfd5e69a3a42"` — stale Sprint 5/6 report ID | STALE DEFAULT | Updated to Sprint 7 report_id `report_05aacb872fda` |
| All `app/pipeline/*.py` — print() calls | All print() calls are inside `if __name__ == "__main__"` guards | PRODUCTION SAFE | Leave unchanged |
| `app/utils/url_scorer.py` — print() calls | print() only inside `if __name__ == "__main__"` guard | PRODUCTION SAFE | Leave unchanged |
| `app/pipeline/graph.py` — 2× TODO comments | MemorySaver TODO + Send fan-out TODO — both are planned future improvements, not debug code | LEAVE UNCHANGED | Noted only |
| `backend/scripts/test_agent1_signal_balance.py` — sprint7_ prefix in logger name | Logger name `sprint7_signal_balance_test` — runtime-irrelevant naming artifact | PRODUCTION SAFE | Leave unchanged |
| `backend/scripts/test_agent1_signal_balance.py` — `_MockLLM` class | Static test mock appropriate for offline signal balance verification; not in production pipeline | PRODUCTION SAFE | Leave unchanged |

---

## Pass 2 Audit Findings (backend/scripts/ and backend/tests/ structural reorganization)

### Target Structure

| Directory | Contents | Classification |
|---|---|---|
| `backend/scripts/` | `demo_track2_ai_hardware_audit.py`, `evidence_quality_audit.py`, `pricing_document_extraction_diagnosis.py` | Primary demo/audit entrypoints |
| `backend/tests/pipeline/` | `test_agent1_expansion_stability.py`, `test_agent1_signal_balance.py` | Zero-cost static regression tests |
| `backend/scripts/diagnostics/` | `full_pipeline_live_audit.py`, `full_pipeline_retrieval_quality_audit.py`, `pricing_pressure_retrieval_audit.py` | Useful diagnostic scripts (require live API) |
| `backend/scripts/archive_pre_submission/` | `test_a2_a3.py` | Stale live integration test |

### Pass 2 Actions

| File | From | To | Path changes |
|---|---|---|---|
| `test_agent1_expansion_stability.py` | `scripts/` | `tests/pipeline/` | `sys.path "../"` → `"../.."` ; artifact dir `"../.."`→ `"../../.."` |
| `test_agent1_signal_balance.py` | `scripts/` | `tests/pipeline/` | `sys.path "../"` → `"../.."` ; `.env "../"` → `"../.."` ; artifact dir `"../.."`→ `"../../.."` ; agent1 source path `"../app"` → `"../../app"` |
| `full_pipeline_live_audit.py` | `scripts/` | `scripts/diagnostics/` | `BACKEND_DIR parents[1]` → `parents[2]` |
| `full_pipeline_retrieval_quality_audit.py` | `scripts/` | `scripts/diagnostics/` | `ROOT parents[2]` → `parents[3]` |
| `pricing_pressure_retrieval_audit.py` | `scripts/` | `scripts/diagnostics/` | `ROOT parents[2]` → `parents[3]` |
| `test_a2_a3.py` | `scripts/` | `scripts/archive_pre_submission/` | No path changes (archived, not run) |

### Pass 2 Verification

| Check | Result |
|---|---|
| Backend import check (`from app.pipeline import graph`) | PASS |
| `tests/pipeline/test_agent1_expansion_stability.py` | PASS (4/4) |
| `tests/pipeline/test_agent1_signal_balance.py` | PASS (15/15) |
| `app/config/` | No violations found | CLEAN | No action |
| `app/api/` | No violations found | CLEAN | No action |
| `app/schemas/` | No violations found | CLEAN | No action |
| argparse in audit scripts | Appropriate for CLI diagnostic tools not used by the pipeline | PRODUCTION SAFE | Leave unchanged |

---

## Detailed Findings

### SHOULD MOVE: `backend/app/pipeline/test_a2_a3.py`

**Issue:** A test file placed inside the production `app/pipeline/` package. Python treats all `.py` files in a package directory as importable modules. Having `test_a2_a3.py` inside the production package creates namespace pollution and implies it is part of the production API surface.

**Evidence:**
- File contains 70+ `print()` statements (diagnostic output, not logging)
- Hardcoded path: `/tmp/test_a2_a3` (ephemeral filesystem location)
- Docstring line 17 references `python -m app.pipeline.test_a2_a3` (module-level invocation)
- Not imported by any production file — confirmed by grep across all `app/` Python files

**Action:** Moved to `backend/scripts/test_a2_a3.py`. Docstring updated to `python backend/scripts/test_a2_a3.py`.

---

### STALE DEFAULT: `backend/scripts/evidence_quality_audit.py` L49-50

**Issue:** `DEFAULT_REPORT_ID = "report_dfd5e69a3a42"` points to a Sprint 5/6 report that no longer exists as the authoritative baseline. Running the script without arguments would audit the wrong report.

**Before:**
```python
DEFAULT_REPORT_ID = "report_dfd5e69a3a42"
DEFAULT_ARTIFACT_DIR = _REPO / "pipeline_audit_artifacts" / "demo_track2_20260526T040110Z"
```

**After:**
```python
DEFAULT_REPORT_ID = "report_05aacb872fda"
DEFAULT_ARTIFACT_DIR = _REPO / "pipeline_audit_artifacts" / "demo_track2_20260526T165950Z"
```

**Note:** The `lstrip`→`removeprefix` bug fix in `extract_domain()` (line 220) was already applied in Sprint 7.1.

---

### STALE DEFAULT: `backend/scripts/pricing_document_extraction_diagnosis.py` L46-47

**Issue:** `_DEFAULT_REPORT_ID = "report_dfd5e69a3a42"` — same stale report ID. Running without arguments would target the wrong artifact directory.

**Before:**
```python
_DEFAULT_REPORT_ID = "report_dfd5e69a3a42"
_DEFAULT_ARTIFACT_DIR = str(_ARTIFACT_ROOT / "demo_track2_20260526T040110Z")
```

**After:**
```python
_DEFAULT_REPORT_ID = "report_05aacb872fda"
_DEFAULT_ARTIFACT_DIR = str(_ARTIFACT_ROOT / "demo_track2_20260526T165950Z")
```

---

### PRODUCTION SAFE: print() in `__main__` guards

All `print()` calls in `app/pipeline/agent1_query_planner.py`, `app/pipeline/agent2_web_collector.py`, `app/pipeline/agent3_fact_extractor.py`, `app/pipeline/agent5_triangulator.py`, `app/pipeline/agent8_report_generator.py`, and `app/utils/url_scorer.py` are gated by `if __name__ == "__main__":`. These do not execute when the modules are imported by the pipeline. No action taken.

---

### LEAVE UNCHANGED: graph.py TODO comments

`app/pipeline/graph.py` contains two TODO comments:
1. `# TODO: Replace MemorySaver with persistent memory backend` — planned infrastructure upgrade
2. `# TODO: Consider using Send for fan-out` — planned LangGraph optimization

Both are scheduled future work, not debug code or temporary hacks. These comments accurately describe intentional deferral decisions. Removing them would lose context for future developers.

---

## Post-Change Verification

After applying the 3 source actions:

| Check | Command | Status |
|---|---|---|
| Backend import check | `python -c "from app.pipeline import graph; print('OK')"` | Run after changes |
| Sprint 5 expansion stability | `python scripts/test_agent1_expansion_stability.py` | Run after changes |
| Sprint 7 signal balance | `python scripts/test_agent1_signal_balance.py` | Run after changes |

If any check fails → stop, do not proceed to artifact cleanup.

---

## What Was NOT Changed

- LangGraph graph definition (`app/pipeline/graph.py`)
- Quality Gate thresholds (`app/pipeline/quality_gate.py`)
- Any agent pipeline logic (agents 1-8)
- Any schema definitions (`app/schemas/`)
- Any API routes (`app/api/`)
- Any configuration files (`app/config/`)
- `.env`
- `backend/data/pulselens.db`
- `frontend/dist/`
- Sprint 7 Agent 1 signal balance fix (`agent1_query_planner.py`)
- Sprint 5 expansion stability fix

No live pipeline was run. No Bright Data or OpenRouter API calls were made.
