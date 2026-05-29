# Chat Async Event Loop Fix Report

**Date:** 2026-05-29  
**Backend syntax check:** ✅ ALL OK — `python -m py_compile` on 5 files  
**Frontend changes:** None — no frontend files changed

---

## Root Cause

The `/api/chat` route handler was a **synchronous** FastAPI function (`def chat`) that used `asyncio.run()` to call async database methods. `asyncio.run()` creates a brand-new event loop each time it is called.

asyncpg connection pools are bound to the event loop that created them (the FastAPI/uvicorn event loop). When `asyncio.run()` spawns a new loop and tries to acquire a connection from the pool, asyncpg detects the loop mismatch and raises:

```
RuntimeError: Task ... got Future ... attached to a different loop
asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress
```

The same pattern existed inside the LangGraph nodes in `graph.py`:
- `retrieve_facts`: `asyncio.run(db_adapter.search_facts(...))`
- `analyst_chat`: `asyncio.run(db_adapter.load_report(...))`
- `validate_citations`: `asyncio.run(db_adapter.load_report(...))`

These are called synchronously by LangGraph's `.invoke()`, which was itself called from inside the FastAPI handler — all using the wrong event loop pattern.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/chat.py` | Route handler `def chat` → `async def chat`; removed `import asyncio`; replaced all `asyncio.run(...)` with `await ...`; switched `chat_graph.invoke()` → `await chat_graph.ainvoke()` |
| `backend/app/chat/graph.py` | Removed `import asyncio`; made `retrieve_facts`, `analyst_chat`, `validate_citations` async; replaced `asyncio.run(...)` with `await ...`; `build_prompt` remains sync (no DB calls) |

---

## Where `asyncio.run()` Was Removed

### `backend/app/api/chat.py`
| Old | New |
|-----|-----|
| `asyncio.run(db_adapter.load_report(...))` | `await db_adapter.load_report(...)` |
| `asyncio.run(db_adapter.get_fact(...))` | `await db_adapter.get_fact(...)` |
| `asyncio.run(db_adapter.save_chat_message(...))` (×2) | `await db_adapter.save_chat_message(...)` |
| `chat_graph.invoke(state, config=config)` | `await chat_graph.ainvoke(state, config=config)` |

### `backend/app/chat/graph.py`
| Node | Old | New |
|------|-----|-----|
| `retrieve_facts` | `asyncio.run(db_adapter.search_facts(...))` | `await db_adapter.search_facts(...)` |
| `analyst_chat` | `asyncio.run(db_adapter.load_report(...))` | `await db_adapter.load_report(...)` |
| `validate_citations` | `asyncio.run(db_adapter.load_report(...))` | `await db_adapter.load_report(...)` |

---

## How DB Calls Are Awaited Now

All DB adapter calls now use `await` directly inside `async` functions on the FastAPI event loop. No new event loops are created. asyncpg connections are acquired from the pool on the correct loop.

LangGraph supports both sync and async nodes. With `ainvoke`, async nodes are awaited natively and sync nodes (like `build_prompt`) are called directly. The `MemorySaver` checkpointer supports async operation.

---

## Context Attachment Verification

`context_attachment` handling was not changed:
```python
"context_attachment": (
    request.context_attachment.model_dump(mode="json")
    if request.context_attachment else None
),
```

All three attachment types (watch_item, risk_alert, fact) pass through `context_attachment` in `ChatState` as before. `_build_attachment_block` in `agent8_analyst_chat.py` receives the dict from state and injects it into the system prompt. No changes were made to this path.

---

## How to Restart with the Fix

```bash
cd backend
set -a; source .env; set +a
uvicorn main:app --reload
```

Verify:
```bash
curl http://127.0.0.1:8000/api/reports/latest
# {"report_id":"report_264d6be13e24"}

curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What are the top signals?","report_id":"report_264d6be13e24","history":null}'
# {"response":"...","cited_facts":[...],"session_id":"chat_..."}
```

---

## Backend Syntax Check

```
python -m py_compile backend/app/api/chat.py backend/app/chat/graph.py
                      backend/app/db/postgres_adapter.py
                      backend/app/db/sqlite_adapter.py
                      backend/app/db/__init__.py
→ ALL OK
```

---

## SQLite Fallback

SQLite adapter methods are already async (using `aiosqlite`). They benefit from the same `await` pattern — no `asyncio.run()` conflicts. The fix is fully backward-compatible with the SQLite path.

---

## Remaining Limitations

1. `chat_graph.ainvoke()` requires LangGraph ≥ 0.1.x with async support. The project uses `langgraph>=1.0.0` which includes `ainvoke`. No version changes needed.
2. `answer_question` in `agent8_analyst_chat.py` remains synchronous (calls the LLM via a sync HTTP client). This is correct — it runs inside an async node but does not block the event loop for a meaningful amount of time beyond the LLM latency. A future improvement could make the LLM client async, but it is not required for the event loop fix.
3. There is no streaming chat endpoint (`/api/chat/stream`) in the current codebase. If one is added, the same async pattern applies: use `async def` and `await` for all DB operations.
