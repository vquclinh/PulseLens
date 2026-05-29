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

# Match [fact_xxx] and [claim_xxx] in LLM output
_FACT_REF_RE = re.compile(r"\[(fact_[A-Za-z0-9_]+)\]")
_CLAIM_REF_RE = re.compile(r"\[(claim_[A-Za-z0-9_-]+)\]")


def _number_citations(text: str, cited_fact_ids: list[str]) -> str:
    """
    Replace internal [fact_xxx] refs with user-friendly [1], [2], … citations.
    claim_xxx refs (from citation-validation retry notes) are stripped entirely.
    The order of cited_fact_ids determines the citation numbers so the
    returned cited_facts list stays in sync: cited_facts[0] ↔ [1], etc.
    """
    mapping = {fid: str(i + 1) for i, fid in enumerate(cited_fact_ids)}

    def _sub_fact(m: re.Match) -> str:
        num = mapping.get(m.group(1))
        return f"[{num}]" if num else ""          # drop unknown refs silently

    text = _FACT_REF_RE.sub(_sub_fact, text)
    text = _CLAIM_REF_RE.sub("", text)            # strip claim refs unconditionally
    text = re.sub(r"  +", " ", text).strip()
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

    # Replace internal [fact_xxx] refs with numbered [1], [2], … for the user.
    # cited_facts is built in the same order as cited_fact_ids so the indices align.
    response = _number_citations(raw_response, cited_fact_ids)

    await db_adapter.save_chat_message(session_id, "user", request.query)
    await db_adapter.save_chat_message(session_id, "assistant", response)

    return ChatResponse(
        response=response,
        cited_facts=cited_facts,
        session_id=session_id,
    )
