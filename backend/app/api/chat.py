# Chat API — POST /api/chat runs RAG over stored facts and returns grounded response.
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from langchain_core.runnables import RunnableConfig

from app.chat.graph import chat_graph
from app.chat.state import ChatState
from app.db import db_adapter
from app.schemas.models import ChatRequest, ChatResponse
from app.utils.helpers import generate_uuid

router = APIRouter(prefix="/api")


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

    # ainvoke instead of invoke — runs async graph nodes in the same event loop.
    result = await chat_graph.ainvoke(state, config=config)

    cited_facts = []
    for fact_id in result.get("cited_fact_ids", []):
        fact = await db_adapter.get_fact(request.report_id, fact_id)
        if fact is not None:
            cited_facts.append(fact)

    response = result.get("response", "")
    await db_adapter.save_chat_message(session_id, "user", request.query)
    await db_adapter.save_chat_message(session_id, "assistant", response)

    return ChatResponse(
        response=response,
        cited_facts=cited_facts,
        session_id=session_id,
    )
