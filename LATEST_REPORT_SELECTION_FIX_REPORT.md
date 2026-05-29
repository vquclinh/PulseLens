# Latest Report Selection Fix Report

**Date:** 2026-05-29  
**Backend syntax check:** ✅ PASS — all 5 files compiled clean  
**Frontend build:** ✅ PASS (no frontend changes) — 5.91s, 0 errors

---

## Root Cause

`main.py` imported `from app.api import report, chat, stock` **before** loading the `.env` file. `app/db/__init__.py` creates `db_adapter` as a module-level singleton at import time by reading the `DATABASE_BACKEND` environment variable. Since `.env` was never loaded, `DATABASE_BACKEND` was not set in the process environment, and `_build_adapter()` fell back to the default `"sqlite"`.

The running FastAPI server was therefore reading from the local `backend/pulselens.db` SQLite file, which only contains the old report `report_e68e7289fc30` (pulse_score=52.7). The Supabase/Postgres database had the newer `report_264d6be13e24` (pulse_score=53.2), but the API never reached Postgres.

The direct Python test worked because it explicitly exported `DATABASE_BACKEND=postgres` in the shell before running.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/main.py` | Added `from dotenv import load_dotenv; load_dotenv()` as the **first two lines** before all other imports |
| `backend/app/db/__init__.py` | Added `logging` to `_build_adapter()` — emits backend name + whether DATABASE_URL is present at startup |
| `backend/app/db/postgres_adapter.py` | Fixed `latest_report_id` ORDER BY: now uses `generated_at DESC NULLS LAST, created_at DESC NULLS LAST` instead of just `created_at DESC` |
| `backend/scripts/check_latest_report.py` | New script for runtime verification |

No frontend changes were needed.

---

## Why `load_dotenv()` Must Be First

Python module-level code runs at first import. The chain is:

```
main.py: from app.api import report, chat, stock
  → app/api/report.py: from app.db import db_adapter
    → app/db/__init__.py: db_adapter = _build_adapter()
      → reads DATABASE_BACKEND env var (defaults to "sqlite" if not set)
```

If `load_dotenv()` is called AFTER this chain, `db_adapter` is already built with the wrong backend. `load_dotenv()` has no effect on the already-created singleton.

The fix puts `load_dotenv()` before all `from app.*` imports in `main.py`. `load_dotenv()` is also a no-op if the vars are already set in the shell, so passing `DATABASE_BACKEND=postgres uvicorn ...` still works.

---

## How to Start Uvicorn Correctly

Any of these will work:

```bash
# Using .env file (recommended — fix makes this work automatically)
cd backend
uvicorn main:app --reload

# Explicit env override (still works)
cd backend
DATABASE_BACKEND=postgres uvicorn main:app --reload

# With the full env loaded in shell first
cd backend
set -a; source .env; set +a
uvicorn main:app --reload
```

The `.env` fix means the first form (plain `uvicorn main:app`) now works correctly.

---

## Postgres `latest_report_id` Query Fix

Old query:
```sql
SELECT report_id FROM reports
WHERE report_id LIKE 'report_%'
ORDER BY created_at DESC LIMIT 1
```

New query:
```sql
SELECT report_id FROM reports
WHERE report_id LIKE 'report_%'
ORDER BY generated_at DESC NULLS LAST,
         created_at  DESC NULLS LAST
LIMIT 1
```

`generated_at` is the pipeline's timestamp (when the report was produced). It is the semantically correct field for "most recent report". `created_at` is the DB insertion timestamp (fallback tie-break). The old query happened to work for the current two reports because the newer report was also inserted more recently, but ordering by `generated_at` is more correct and robust.

---

## Startup Logging Added

After the fix, uvicorn startup logs will include:

```
INFO  app.db:__init__.py  db_adapter: building adapter for backend=postgres
INFO  app.db:__init__.py  db_adapter: DATABASE_URL present=true
INFO  app.db:__init__.py  db_adapter: PostgresAdapter created (host masked)
INFO  main:main.py  Database backend selected: postgres
INFO  main:main.py  DATABASE_URL present: true
```

No secrets are logged. The full DATABASE_URL is never emitted.

If misconfigured (SQLite running by mistake), the log will show:
```
INFO  app.db:__init__.py  db_adapter: building adapter for backend=sqlite
```

---

## Runtime Verification

After restart with the fix, `/api/reports/latest` should return:
```json
{"report_id": "report_264d6be13e24"}
```

And:
```bash
curl -s http://127.0.0.1:8000/api/report/report_264d6be13e24 | python -m json.tool | grep pulse_score
```
should show:
```
"pulse_score": 53.2,
```

Use the new script for a quick check:
```bash
cd backend
python scripts/check_latest_report.py
```

Expected output:
```
DATABASE_BACKEND : postgres
DATABASE_URL set : true

Latest report_id : report_264d6be13e24
generated_at     : 2026-05-28T04:05:46.203748+00:00
pulse_score      : 53.2
pulse_status     : stable
quality_status   : PASS
evidence_count   : 64
source_count     : 29
fact rows loaded : 64

OK — latest report loaded successfully.
```

---

## Frontend Cache/Query Analysis

No frontend changes needed. The frontend does not cache stale report IDs:

- `fetchLatestReportId()` is called on workspace mount with no `staleTime` override → defaults to React Query default (stale immediately, refetches on remount)
- `workspaceReport` query has `staleTime: 5 * 60 * 1000` (5 min) — keyed by `latestReportId`, so a new report ID from the API automatically triggers a fresh fetch
- `workspaceFacts` query has `staleTime: 10 * 60 * 1000` (10 min) — same, keyed by ID
- Only `demo-baseline.ts` contains `report_e68e7289fc30`, correctly labeled as `DEMO_REPORT_ID` — it is only used in the Home page fallback, not in the Workspace

---

## SQLite Fallback Still Works

If `DATABASE_BACKEND` is not set (or set to `"sqlite"`), the adapter builds as before. The `load_dotenv()` call is a no-op when the var is missing. No changes were made to `sqlite_adapter.py` or `database.py`.

---

## Confirmation: No Hardcoded Report IDs

```
rg "report_e68e7289fc30|report_264d6be13e24" frontend/src backend/app
```
Only `demo-baseline.ts` (labeled fallback constant). No hardcoded IDs in any live route or adapter.

---

## Build/Compile Results

```
python -m py_compile backend/app/db/__init__.py backend/app/db/postgres_adapter.py
                      backend/app/api/report.py backend/main.py
                      backend/scripts/check_latest_report.py
→ ALL OK

cd frontend && npm run build
→ ✓ built in 5.91s — 0 errors, 0 warnings
```

---

## Remaining Limitations

1. If the process environment has `DATABASE_BACKEND` set to something other than `postgres` via a system service file (systemd, Docker env, etc.), the `.env` file's setting will NOT override it — `load_dotenv()` respects existing env vars by default. Use `load_dotenv(override=True)` only if you explicitly want the file to win over the system environment.
2. The `db_adapter` singleton is created once per process. Hot-reloading the `.env` file does not change the adapter — a restart is required.
3. The `check_latest_report.py` script must be run from `backend/` so that `app.*` imports resolve correctly.
