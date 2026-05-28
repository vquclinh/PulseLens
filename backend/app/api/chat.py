# Chat API — POST /api/chat runs RAG over stored facts and returns grounded response.
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from langchain_core.runnables import RunnableConfig

from app.chat.graph import chat_graph
from app.chat.state import ChatState
from app.db import db_adapter
from app.schemas.models import ChatRequest, ChatResponse
from app.utils.helpers import generate_uuid

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    report = asyncio.run(db_adapter.load_report(request.report_id))
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
    }
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}
    result = chat_graph.invoke(
        state,
        config=config,
    )

    cited_facts = []
    for fact_id in result.get("cited_fact_ids", []):
        fact = asyncio.run(db_adapter.get_fact(request.report_id, fact_id))
        if fact is not None:
            cited_facts.append(fact)

    response = result.get("response", "")
    asyncio.run(db_adapter.save_chat_message(session_id, "user", request.query))
    asyncio.run(db_adapter.save_chat_message(session_id, "assistant", response))

    return ChatResponse(
        response=response,
        cited_facts=cited_facts,
        session_id=session_id,
    )
