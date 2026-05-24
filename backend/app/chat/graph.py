# Chat LangGraph StateGraph — per-session analyst chat (Self-RAG + FLARE)
# Nodes are placeholders; real Agent 8 wired in a later task.
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.chat.state import ChatState

logger = logging.getLogger(__name__)


# ── Placeholder node functions ─────────────────────────────────────────────────

def retrieve_facts(state: ChatState) -> dict:
    """Semantic search over fact embeddings for this report (Self-RAG retrieve step)"""
    logger.info("node: retrieve_facts")
    return {}


def build_prompt(state: ChatState) -> dict:
    """Inject retrieved evidence + last 5 history exchanges into LLM prompt"""
    logger.info("node: build_prompt")
    return {}


def analyst_chat(state: ChatState) -> dict:
    """Agent 8 — Analyst Chat (Self-RAG arXiv:2310.11511 + FLARE arXiv:2305.06983)"""
    logger.info("node: analyst_chat")
    return {}


def validate_citations(state: ChatState) -> dict:
    """Validate all [fact_id] citations in response exist in DB; retry once if not"""
    logger.info("node: validate_citations")
    return {}


# ── Build and compile graph ────────────────────────────────────────────────────

_builder = StateGraph(ChatState)

_builder.add_node("retrieve_facts",     retrieve_facts)
_builder.add_node("build_prompt",       build_prompt)
_builder.add_node("analyst_chat",       analyst_chat)
_builder.add_node("validate_citations", validate_citations)

_builder.add_edge(START,                "retrieve_facts")
_builder.add_edge("retrieve_facts",     "build_prompt")
_builder.add_edge("build_prompt",       "analyst_chat")
_builder.add_edge("analyst_chat",       "validate_citations")
_builder.add_edge("validate_citations", END)

# No checkpointer — session history is stored in ChatState.history
chat_graph = _builder.compile()
