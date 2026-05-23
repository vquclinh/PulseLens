# ChatState — LangGraph TypedDict for the per-session analyst chat graph
from __future__ import annotations
from typing import TypedDict, List

from app.schemas.models import ChatMessage, FactObject


class ChatState(TypedDict):
    report_id: str
    history: List[ChatMessage]      # last 5 exchanges (trimmed for context budget)
    current_query: str
    retrieved_facts: List[FactObject]
    response: str
    cited_fact_ids: List[str]
    retrieval_rounds: int           # tracks FLARE active retrieval iterations
