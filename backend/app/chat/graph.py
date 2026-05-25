# Chat LangGraph StateGraph — per-session analyst chat (Self-RAG + FLARE-inspired)
from __future__ import annotations

import logging
import re
import asyncio

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.chat.agent8_analyst_chat import answer_question, build_evidence_block
from app.chat.state import ChatState
from app.db.database import load_report, search_facts

logger = logging.getLogger(__name__)

_FACT_REF_RE = re.compile(r"\[(fact_[A-Za-z0-9_]+)\]")


def retrieve_facts(state: ChatState) -> dict:
    """Semantic search over fact embeddings for this report."""
    report_id = state["report_id"]
    query = state["current_query"]
    logger.info("chat node: retrieve_facts report=%s", report_id)
    facts = asyncio.run(search_facts(report_id, query, top_k=10))
    return {
        "retrieved_facts": facts,
        "retrieval_rounds": state.get("retrieval_rounds", 0),
    }


def build_prompt(state: ChatState) -> dict:
    """Store the evidence block for observability/debugging."""
    logger.info("chat node: build_prompt facts=%d", len(state.get("retrieved_facts") or []))
    return {"prompt": build_evidence_block(state.get("retrieved_facts") or [])}


def analyst_chat(state: ChatState) -> dict:
    """Agent 8 — grounded answer over retrieved facts."""
    logger.info("chat node: analyst_chat")
    report = asyncio.run(load_report(state["report_id"]))
    response = answer_question(
        query=state["current_query"],
        retrieved_facts=state.get("retrieved_facts") or [],
        history=state.get("history") or [],
        report=report,
    )
    return {"response": response}


def validate_citations(state: ChatState) -> dict:
    """
    Validate all [fact_id] citations in the response.

    On one validation failure, retry Agent 8 with an explicit correction note
    using the same retrieved evidence. This matches the architecture's
    "retry with hallucinated IDs listed" behavior without looping the graph.
    """
    logger.info("chat node: validate_citations")
    facts = state.get("retrieved_facts") or []
    valid_ids = {fact.fact_id for fact in facts}
    cited = _extract_citations(state.get("response", ""))
    invalid = sorted(set(cited) - valid_ids)
    if not invalid:
        return {"cited_fact_ids": cited, "invalid_citations": []}

    report = asyncio.run(load_report(state["report_id"]))
    retry_note = (
        f"User question: {state['current_query']}\n\n"
        "The previous response cited fact IDs that are not in the retrieved "
        f"evidence: {', '.join(invalid)}.\n"
        "Rewrite the answer using only the fact IDs in the Evidence section. "
        "If the evidence is insufficient, say so."
    )
    response = answer_question(
        query=state["current_query"],
        retrieved_facts=facts,
        history=state.get("history") or [],
        report=report,
        retry_note=retry_note,
    )
    cited = _extract_citations(response)
    invalid = sorted(set(cited) - valid_ids)
    return {
        "response": response,
        "cited_fact_ids": cited,
        "invalid_citations": invalid,
    }


def _extract_citations(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for fact_id in _FACT_REF_RE.findall(text or ""):
        if fact_id not in seen:
            seen.add(fact_id)
            ordered.append(fact_id)
    return ordered


_builder = StateGraph(ChatState)

_builder.add_node("retrieve_facts", retrieve_facts)
_builder.add_node("build_prompt", build_prompt)
_builder.add_node("analyst_chat", analyst_chat)
_builder.add_node("validate_citations", validate_citations)

_builder.add_edge(START, "retrieve_facts")
_builder.add_edge("retrieve_facts", "build_prompt")
_builder.add_edge("build_prompt", "analyst_chat")
_builder.add_edge("analyst_chat", "validate_citations")
_builder.set_finish_point("validate_citations")

chat_graph = _builder.compile(checkpointer=MemorySaver())
