# System Evaluation Run Plan

**Created:** 2026-05-27  
**Purpose:** Clean, honest health check + one full demo-scope pipeline regression.  
**Constraints:** No patching, no optimization, no threshold changes, no fake evidence, no full 8-company mode, no forensic instrumentation in core runtime files. Run expensive pipeline at most once.

---

## 1. Current Git State

| Item | Value |
|---|---|
| Branch | `main` |
| Working tree | **Clean** (confirmed at plan time) |
| Last commit | `09ec913 docs: add Claude Code project guide` |
| Ahead of origin | 1 commit |
| Uncommitted changes | None |

### Reset Confirmation

| File | Expected (reset) | Actual |
|---|---|---|
| `backend/app/utils/forensic_tracer.py` | absent | **absent** ✅ |
| `llm_client.py` `self._agent_name` | absent | **absent** ✅ |
| `graph.py` `_traced_node` wrapper | absent | **absent** ✅ |
| `brightdata_client.py` forensic hook | absent | **absent** ✅ |
| Hardcoded report IDs in runtime code | absent | **absent** ✅ |
| `force_pass` / `bypass_quality` flags | absent | **absent** ✅ |

**Reset appears complete.** Core pipeline files are clean.

---

## 2. Code Files Inspected

| File | What it tells us |
|---|---|
| `backend/app/pipeline/graph.py` | LangGraph DAG — no tracing wrappers |
| `backend/app/utils/llm_client.py` | OpenRouter wrapper — no forensic hooks |
| `backend/app/utils/brightdata_client.py` | BrightData wrapper — no forensic hooks |
| `backend/app/config/quality_gates.py` | Thresholds: min_facts=50, min_source_count=15 |
| `backend/app/config/demo_scope.py` | Companies: Nvidia/AMD/Supermicro; 4 core signals |
| `backend/scripts/demo_track2_ai_hardware_audit.py` | Live pipeline runner |
| `backend/scripts/evidence_quality_audit.py` | Zero-cost DB audit |
| `backend/scripts/pricing_document_extraction_diagnosis.py` | Zero-cost pricing gap audit |
| `backend/tests/pipeline/test_agent1_expansion_stability.py` | Sprint 5 crash guard |
| `backend/tests/pipeline/test_agent1_signal_balance.py` | Sprint 7 signal balance guard |

---

## 3. Quality Gate Thresholds (from `quality_gates.py`)

```
min_facts                  = 50
min_source_count           = 15
min_signal_types           = 7
min_company_coverage_ratio = 0.75
max_zero_doc_query_rate    = 0.35
max_fetch_error_rate       = 0.35
MAX_EXPANSION_ROUNDS       = 2
```

---

## 4. Zero-Cost Checks Before Live Pipeline

All run from `backend/`:

| # | Command | Log file | Cost |
|---|---|---|---|
| 1 | `python -c "from app.pipeline import graph; print('pipeline import OK')"` | `backend_import_check.log` | $0 |
| 2 | `python -c "from main import app; print('FastAPI import OK')"` | `fastapi_import_check.log` | $0 |
| 3 | `python tests/pipeline/test_agent1_expansion_stability.py` | `agent1_expansion_stability_test.log` | $0 |
| 4 | `python tests/pipeline/test_agent1_signal_balance.py` | `agent1_signal_balance_test.log` | $0 |
| 5 | `cd ../frontend && npm run build` | `frontend_build.log` | $0 |

**If any check fails:** Create `SYSTEM_EVALUATION_FAILURE_REPORT.md` → stop → no live pipeline.

---

## 5. Static Safety Scan

Grep in `backend/app/` (excluding `.venv/`, `__pycache__/`, `tests/`, `*.md`):

| Pattern | Flagged if found in |
|---|---|
| `force_pass` | any runtime file |
| `bypass_quality` | any runtime file |
| `skip_gate` | any runtime file |
| `fake_evidence` | any runtime file |
| `PULSELENS_FORENSIC_TRACE.*true` | any `app/` file (as hardcoded default-true) |
| `forensic_tracer` | any `app/` runtime file |
| `report_[0-9a-f]{8,}` | `app/pipeline/`, `app/config/` |
| `test_*.py` files | `app/pipeline/` directory |

Output: `static_safety_scan.json` + `static_safety_scan.md`

---

## 6. Exact Live Pipeline Command

```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py \
  2>&1 | tee <system_eval_dir>/live_pipeline_terminal.log
```

The script auto-creates:
```
pipeline_audit_artifacts/demo_track2_<YYYYMMDDTHHMMSSZ>/
├── pipeline_run.log
├── demo_scope_config.json
├── query_planner_audit.json
├── web_collection_audit.json
├── quality_gate_audit.json
├── fetch_error_summary.json
├── final_report_quality_summary.json
└── demo_report_summary.json
```

---

## 7. Artifact Folder Structure

```
pipeline_audit_artifacts/system_evaluation_<YYYYMMDDTHHMMSSZ>/
├── 00_git_status_before.txt
├── 01_environment_readiness_redacted.json
├── 02_command_manifest.json
├── backend_import_check.log
├── fastapi_import_check.log
├── agent1_expansion_stability_test.log
├── agent1_signal_balance_test.log
├── frontend_build.log
├── static_safety_scan.json
├── static_safety_scan.md
├── live_pipeline_terminal.log
├── evidence_quality_terminal.log          (if report_id created)
├── pricing_diagnosis_terminal.log         (if report_id created)
├── SYSTEM_EVALUATION_FAILURE_REPORT.md    (if any check failed)
├── SYSTEM_EVALUATION_REPORT.md
├── SYSTEM_EVALUATION_ARTIFACTS.md
└── review_bundle/
    ├── (copies of key files for ChatGPT review)
    └── ...
```

---

## 8. Logs and Metrics Captured

From the live pipeline run:
- `report_id`, `quality_status`, `quality_reasons`
- `evidence_count`, `source_count`, `query_count`, `accepted_doc_count`
- `zero_doc_query_rate`, `fetch_error_rate`
- `covered_signal_types`, `missing_signal_types`
- `companies_covered`, `core_signals_covered/missing`, `optional_signals_covered/missing`
- `pricing_pressure_document_count`, `estimated_brightdata_calls`
- Per-signal fact counts, watch list items
- FinBERT sentiment breakdown (pos/neg/neu)
- Verified claims count, suspicious claims count
- SAFE pass rate

---

## 9. Expected Cost Risk

| Component | Estimate |
|---|---|
| OpenRouter / Gemini 2.5 Flash | ~$0.06–$0.10 |
| BrightData SERP queries | ~$0.22–$0.32 |
| BrightData page scrapes | ~$0.20–$1.20 |
| FinBERT (local CPU) | **$0.00** |
| Zero-cost checks | **$0.00** |
| **Total estimated** | **$0.50–$1.60** |

**Note:** FinBERT model load takes ~60–70 minutes on CPU in this environment. Plan for a 90-minute window for the live pipeline.

---

## 10. Failure Handling

| Scenario | Action |
|---|---|
| Any zero-cost check fails | Write `SYSTEM_EVALUATION_FAILURE_REPORT.md`, stop |
| Static safety scan finds bypass code | Flag in report, abort live pipeline |
| Live pipeline raises exception | Save partial artifacts, record in SYSTEM_EVALUATION_REPORT.md, stop |
| Live pipeline times out | Save what exists, mark as failed in report |
| No report_id created | Skip evidence_quality + pricing_diagnosis, note in report |

**Do NOT** retry the pipeline. **Do NOT** patch after seeing results.

---

## 11. Files to Send to ChatGPT for Review

From `review_bundle/`:

1. `SYSTEM_EVALUATION_REPORT.md` — primary summary (all 31 questions)
2. `01_environment_readiness_redacted.json` — env config + thresholds
3. `final_report_quality_summary.json` — quality gate verdict
4. `quality_gate_audit.json` — full gate decision fields
5. `demo_report_summary.json` — report + signal/company coverage
6. `evidence_quality_summary.json` — signal semantics, suspicious claims count
7. `suspicious_claims.json` — flagged facts
8. `pricing_pressure_semantics_audit.json` — pricing gap analysis
9. `query_planner_audit.json` — Agent 1 telemetry
10. `web_collection_audit.json` — Agent 2 collection stats
11. `static_safety_scan.json` — safety scan results
