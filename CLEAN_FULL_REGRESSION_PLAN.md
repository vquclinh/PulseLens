# Clean Full Regression Plan

**Created:** 2026-05-26
**Purpose:** Stabilize Sprint 4 state, archive stale artifacts, run one clean full demo-scope regression.

---

## 1. Current Sprint 4 Status

### Background process status
**All processes terminated.** The background demo run (PID 120509/120511) completed with EXIT_CODE:0
before this plan was written. No lingering pipeline processes.

### Sprint 4 code changes (in place, not committed)
Four backend files modified since last commit:
- `backend/app/utils/url_scorer.py` — COMPANY_IR_DOMAINS + IR-nav rejection
- `backend/app/pipeline/node_validate_and_split.py` — metadata/nav guard + pricing sanity filter
- `backend/app/pipeline/state.py` — validation_audit field
- `backend/app/pipeline/graph.py` — unpack validate_facts tuple

New untracked files: 5 markdown reports, 1 new script, 4 new artifact folders.

### DB state (latest reports)
| Report ID | Created | Status | Score | Facts |
|---|---|---|---|---|
| `report_3dfb4b94068b` | 2026-05-26 06:40 | PARTIAL_PASS | 57.0 | 43 |
| `report_dfd5e69a3a42` | 2026-05-26 04:07 | PASS | 44.3 | 63 |
| `report_ce3edef53b1f` | 2026-05-26 04:00 | PARTIAL_PASS | 51.0 | 48 |

`report_3dfb4b94068b` is the Sprint 4 result. It is the most recent and most clean.

---

## 2. Folder Assessment

### Complete and authoritative — KEEP

| Folder | Status | Files | Keep? |
|---|---|---|---|
| `demo_track2_20260526T040110Z/` | Sprint 2 baseline — authoritative | 8 files | YES |
| `demo_track2_20260526T063140Z/` | Sprint 4 complete run (EXIT_CODE:0) | 8 files | YES |
| `evidence_quality_20260526T053621Z/` | Sprint 3 audit | 6 files | YES |
| `evidence_quality_20260526T064101Z/` | Sprint 4 audit | 6 files | YES |
| `pricing_extraction_diagnosis_20260526T061730Z/` | Sprint 4 gap diagnosis | 4 files | YES |
| `pricing_pressure_20260526T033831Z/` | Sprint 2 pricing retrieval | multiple | YES |
| `archive_sprint2_stale/` | 9 stale Sprint 2 runs | already archived | YES |
| `archive_sprint4_stale/` | 2 incomplete Sprint 4 runs | already archived | YES |

### Stale — ARCHIVE before regression

All stale folders are already inside `archive_sprint4_stale/`. The live artifact tree is clean.
Nothing further needs to be moved before the regression.

---

## 3. What Will Be Archived

The archive step will create:
```
pipeline_audit_artifacts/archive_before_full_regression_<ts>/
```
And move into it:
- (none required — all live stale folders are already in archive_sprint4_stale)

The archive folder will be created as a record even if empty, with a manifest.

---

## 4. Exact Commands to Run

### Step 0 — Pre-flight
```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens
git status > full_regression_<ts>/git_status_before.txt
python -c "import app.utils.url_scorer; import app.pipeline.graph; print('OK')"
```

### Step 1 — Backend compile/import checks (zero cost)
```bash
cd backend
python -c "
import app.utils.url_scorer
import app.pipeline.node_validate_and_split
import app.pipeline.state
import app.pipeline.graph
import scripts.pricing_document_extraction_diagnosis
print('all OK')
"
```

### Step 2 — Demo pipeline (BrightData + OpenRouter cost)
```bash
python backend/scripts/demo_track2_ai_hardware_audit.py \
  2>&1 | tee full_regression_<ts>/demo_pipeline_terminal.log
```
Expected runtime: ~15–20 minutes (2 rounds if quality gate requires expansion).
Expected cost: ~118 BrightData SERP + scraper calls, ~115 OpenRouter calls.
Scope: Nvidia, AMD, Supermicro — demo_scope_enabled=true.

### Step 3 — Evidence quality audit (zero cost)
```bash
python backend/scripts/evidence_quality_audit.py \
  --report-id <new_report_id> \
  --artifact-dir pipeline_audit_artifacts/demo_track2_<new_ts>/ \
  2>&1 | tee full_regression_<ts>/evidence_quality_terminal.log
```

### Step 4 — Pricing gap diagnosis (zero cost)
```bash
python backend/scripts/pricing_document_extraction_diagnosis.py \
  --report-id <new_report_id> \
  --artifact-dir pipeline_audit_artifacts/demo_track2_<new_ts>/ \
  2>&1 | tee full_regression_<ts>/pricing_diagnosis_terminal.log
```

### Step 5 — Frontend build (zero API cost)
```bash
cd frontend && npm run build 2>&1 | tee ../full_regression_<ts>/frontend_build.log
```

---

## 5. BrightData / OpenRouter Cost Risk

| Step | Cost |
|---|---|
| Import checks | Zero |
| Evidence audit | Zero (DB read) |
| Pricing diagnosis | Zero (DB + file read) |
| Frontend build | Zero |
| Demo pipeline round 0 | ~80 BrightData SERP + ~36 OpenRouter Agent 3 + ~36 SAFE + ~5 narrative |
| Demo pipeline round 1 (if needed) | ~40 BrightData + ~20 OpenRouter |
| **Total expected** | **~118–140 BrightData + ~115 OpenRouter** |

**Risk level: LOW-MEDIUM.** Same as Sprint 4 demo run. Acceptable.

---

## 6. Expected Output Artifact Paths

```
pipeline_audit_artifacts/
  full_regression_<ts>/
    git_status_before.txt
    environment_readiness_redacted.json
    command_manifest.json
    backend_compile.log
    backend_import_check.log
    demo_pipeline_terminal.log
    evidence_quality_terminal.log
    pricing_diagnosis_terminal.log
    frontend_build.log
    git_status_after.txt
    review_bundle/
      final_report_quality_summary.json
      demo_report_summary.json
      query_planner_audit.json
      web_collection_audit.json
      quality_gate_audit.json
      fetch_error_summary.json
      evidence_quality_summary.json
      signal_semantics_audit.json
      pricing_pressure_semantics_audit.json
      suspicious_claims.json
      source_tier_quality_audit.json
      pricing_extraction_gap_summary.json
      pipeline_run.log
      demo_pipeline_terminal.log
      evidence_quality_terminal.log

  demo_track2_<new_ts>/          (created by demo script)
  evidence_quality_<new_ts>/     (created by audit script)
  pricing_extraction_diagnosis_<new_ts>/  (created by diagnosis script)
  archive_before_full_regression_<ts>/   (empty — all stale already archived)
```

---

## 7. Rollback / Safety Strategy

- **No files will be deleted permanently.** Only `mv` to archive folders.
- **DB is not touched** — pipeline writes new rows, does not modify existing ones.
- **Sprint 4 artifacts** (`demo_track2_20260526T063140Z/`, `evidence_quality_20260526T064101Z/`) are kept and remain authoritative until the fresh regression produces a better result.
- **If the fresh pipeline fails once:** Stop. Document the failure. Write weakness report based on the Sprint 4 run (`report_3dfb4b94068b`). Do not retry.
- **If PARTIAL_PASS:** Accept and report honestly. A truthful PARTIAL_PASS (fact_count < 50) is expected and correct given Sprint 4 filtering.
- **If quality_status=FAIL:** Investigate root cause before any further runs.
- **Code rollback:** `git diff` shows the 4 Sprint 4 code changes. `git stash` would revert if needed, but do not do this unless explicitly requested.

---

## 8. Scope Enforcement Checklist

Before running the pipeline, verify:
- [ ] `demo_scope_enabled = True` in `backend/app/config/demo_scope.py`
- [ ] Companies list contains only: Nvidia, AMD, Supermicro
- [ ] Full 8-company mode is NOT triggered
- [ ] No environment variable overrides `demo_scope_enabled`
