# Chat API — POST /api/chat runs RAG over stored facts and returns grounded response.
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from langchain_core.runnables import RunnableConfig

from app.chat.graph import chat_graph
from app.chat.state import ChatState
from app.db import db_adapter
from app.schemas.models import ChatRequest, ChatResponse
from app.utils.helpers import generate_uuid

router = APIRouter(prefix="/api")

def _sanitize_response(text: str, cited_fact_ids: list[str]) -> str:
    """
    Convert every internal ID reference to a user-facing form — or remove it.

    Handles all leakage patterns observed in the wild:
      [fact_abc123]                   → [N]  (single fact ref)
      [fact_abc, fact_def]            → [N][M]  (comma-separated multi-fact)
      [claim_xxx]                     → removed
      [report_264d6be13e24]           → removed  (refer to "this report" instead)
      [fcf22aae99ba]                  → removed  (bare hex hash ≥ 8 chars)

    Preserved (never touched):
      [1], [2], [3]                   → numbered citations already converted
      [text](url)                     → markdown links
    """
    mapping = {fid: str(i + 1) for i, fid in enumerate(cited_fact_ids)}

    # ── Step 1: Multi-fact bracket  [fact_abc, fact_def, ...] ────────────────
    def _expand_multi(m: re.Match) -> str:
        ids = re.findall(r"fact_[A-Za-z0-9_]+", m.group(0))
        parts = [f"[{mapping[fid]}]" for fid in ids if fid in mapping]
        return "".join(parts)

    text = re.sub(
        r"\[fact_[A-Za-z0-9_]+(?:\s*,\s*fact_[A-Za-z0-9_]+)+\]",
        _expand_multi, text,
    )

    # ── Step 2: Single fact ref  [fact_xxx] ──────────────────────────────────
    def _single_fact(m: re.Match) -> str:
        num = mapping.get(m.group(1))
        return f"[{num}]" if num else ""

    text = re.sub(r"\[(fact_[A-Za-z0-9_]+)\]", _single_fact, text)

    # ── Step 3: Claim refs  [claim_xxx, ...] ────────────────────────────────
    text = re.sub(r"\[claim_[A-Za-z0-9_-]+(?:\s*,\s*[A-Za-z0-9_-]+)*\]", "", text)

    # ── Step 4: Report refs  [report_xxx] ───────────────────────────────────
    text = re.sub(r"\[report_[A-Za-z0-9_-]+\]", "", text)

    # ── Step 5: Bare hex hashes  [fcf22aae99ba]  (≥8 hex chars, not Markdown links)
    # Negative lookahead (?!\() keeps Markdown [text](url) untouched.
    text = re.sub(r"\[[a-f0-9]{8,}\](?!\()", "", text)

    # ── Step 6: Tidy up artifacts ────────────────────────────────────────────
    text = re.sub(r"  +", " ", text)           # collapse extra spaces
    text = re.sub(r"\s+([,\.;:!?])", r"\1", text)  # remove space before punctuation
    text = text.strip()
    return text


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Grounded analyst chat over the latest report evidence.

    All DB operations use `await` directly — never asyncio.run() — so asyncpg
    connections stay on the FastAPI event loop and do not conflict with the
    connection pool.
    """
    report = await db_adapter.load_report(request.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    session_id = request.session_id or f"chat_{generate_uuid()[:12]}"
    state: ChatState = {
        "report_id": request.report_id,
        "session_id": session_id,
        "history": request.history or [],
        "current_query": request.query,
        "retrieved_facts": [],
        "response": "",
        "cited_fact_ids": [],
        "retrieval_rounds": 0,
        "errors": [],
        "context_attachment": (
            request.context_attachment.model_dump(mode="json")
            if request.context_attachment else None
        ),
    }
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    # ainvoke keeps all DB calls on the FastAPI event loop.
    result = await chat_graph.ainvoke(state, config=config)

    cited_fact_ids: list[str] = result.get("cited_fact_ids", [])

    cited_facts = []
    for fact_id in cited_fact_ids:
        fact = await db_adapter.get_fact(request.report_id, fact_id)
        if fact is not None:
            cited_facts.append(fact)

    raw_response = result.get("response", "")

    # Convert all internal ID refs to user-facing form (or remove them).
    # cited_facts stays in sync: cited_facts[0] ↔ [1], etc.
    response = _sanitize_response(raw_response, cited_fact_ids)

    await db_adapter.save_chat_message(session_id, "user", request.query)
    await db_adapter.save_chat_message(session_id, "assistant", response)

    return ChatResponse(
        response=response,
        cited_facts=cited_facts,
        session_id=session_id,
    )
