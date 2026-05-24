# Pipeline LangGraph StateGraph — all nodes, edges, quality-gate conditional, SQLite checkpointer
# Node implementations are placeholders; real agents wired in subsequent tasks.
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.config.quality_gates import MAX_EXPANSION_ROUNDS
from app.pipeline.agent1_query_planner import QueryPlanner
from app.pipeline.agent2_web_workers import collect_documents, collect_documents_for_query
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# ── Database path (absolute so it's invariant to cwd) ──────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "pulselens.db"))
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

# ── Node functions ─────────────────────────────────────────────────────────────
# Agent 1 and Agent 2 are implemented; later-stage nodes remain placeholders.

def query_planner(state: PipelineState) -> dict:
    """Agent 1 — Query Planner (Step-Back + Multi-HyDE-inspired fan-out)"""
    expansion_round = state.get("query_expansion_rounds", 0)
    logger.info("node: query_planner (round=%d)", expansion_round)
    planner = QueryPlanner()
    low_signal_types = state.get("low_signal_types") or None
    companies = state.get("companies") or [c.name for c in COMPANIES]
    queries = planner.run(
        market=state.get("market", DEFAULT_MARKET),
        companies=companies,
        time_window=state.get("time_window", DEFAULT_TIME_WINDOW),
        expansion_round=expansion_round,
        low_signal_types=low_signal_types,
    )
    existing = list(state.get("queries") or [])
    return {"queries": existing + queries}   # counter owned by quality_gate


async def web_worker(state: PipelineState) -> dict:
    """Agent 2 — Web Collection Workers (Bright Data, parallel fan-out via Send)"""
    query = state.get("agent2_query")
    if query is not None:
        logger.info("node: web_worker query_id=%s", query.query_id)
        return {"raw_documents": await collect_documents_for_query(query)}

    # Fallback path for direct node testing without Send.
    queries = state.get("queries") or []
    logger.info("node: web_worker fallback batch size=%d", len(queries))
    return {"raw_documents": await collect_documents(queries)}


def fact_extractor(state: PipelineState) -> dict:
    """Agent 3 — Fact Extractors (RASG schema-constrained extraction, parallel fan-out)"""
    logger.info("node: fact_extractor")
    return {}


def validate_fact(state: PipelineState) -> dict:
    """Node — validate_fact: evidence_quote verbatim check, confidence filter"""
    logger.info("node: validate_fact")
    return {}


def validate_and_split(state: PipelineState) -> dict:
    """Node — SAFE Atomic Verification (arXiv:2403.18802)"""
    logger.info("node: validate_and_split")
    return {}


def finbert_scorer(state: PipelineState) -> dict:
    """Agent 4 — FinBERT Scorer (ProsusAI/finbert, batch sentiment)"""
    logger.info("node: finbert_scorer")
    return {}


def quality_gate(state: PipelineState) -> dict:
    """Node — Quality Gate: checks signal coverage, owns query_expansion_rounds counter"""
    logger.info("node: quality_gate")
    scored_facts = state.get("scored_facts") or []
    expansion_rounds = state.get("query_expansion_rounds", 0)

    # Short-circuit: no scored facts yet (upstream nodes are stubs) → pass
    if not scored_facts:
        return {"quality_passed": True}

    # Real check: signal coverage gate (TODO: tune thresholds with real data)
    covered = {f["signal_type"] for f in scored_facts if isinstance(f, dict)}
    if len(covered) < 4 and expansion_rounds < MAX_EXPANSION_ROUNDS:
        from app.schemas.models import SignalType
        all_signal_types = {st.value for st in SignalType}
        return {
            "quality_passed": False,
            "query_expansion_rounds": expansion_rounds + 1,
            "low_signal_types": sorted(all_signal_types - covered),
        }

    return {"quality_passed": True}


def triangulator(state: PipelineState) -> dict:
    """Node — M4 Triangulator (ClaimCheck + MiniCheck + FActScore)"""
    logger.info("node: triangulator")
    return {}


def contradiction_writer(state: PipelineState) -> dict:
    """Agent 5 — Contradiction Writers (parallel fan-out per contradicted pair)"""
    logger.info("node: contradiction_writer")
    return {}


def signal_scorer(state: PipelineState) -> dict:
    """Node — M5 Signal Scorer (weighted formula: tier × recency × factscore)"""
    logger.info("node: signal_scorer")
    return {}


def narrative_synthesizer(state: PipelineState) -> dict:
    """Agent 6 — Narrative Synthesizer (STORM multi-perspective, arXiv:2402.14207)"""
    logger.info("node: narrative_synthesizer")
    return {}


def watch_list_builder(state: PipelineState) -> dict:
    """Agent 7 — Watch List Builder (forward indicators from unresolved signals)"""
    logger.info("node: watch_list_builder")
    return {}


def report_assembler(state: PipelineState) -> dict:
    """Node — Report Assembler: assembles MarketPulseReport, saves to SQLite"""
    logger.info("node: report_assembler")
    return {}


# ── Quality gate router ────────────────────────────────────────────────────────

def _fanout_web_workers(state: PipelineState) -> list[Send]:
    queries = state.get("queries") or []
    if not queries:
        return [Send("web_worker", {"agent2_query": None})]
    return [Send("web_worker", {"agent2_query": query}) for query in queries]


def _quality_gate_router(state: PipelineState) -> Literal["expand_queries", "proceed"]:
    """
    Routes after quality_gate node.
    placeholder: always proceeds; real logic lives in node_quality_gate.py.
    """
    if not state.get("quality_passed", True):
        return "expand_queries"
    return "proceed"


# ── Build and compile graph ────────────────────────────────────────────────────

_builder = StateGraph(PipelineState)

# Register all nodes
_builder.add_node("query_planner",       query_planner)
_builder.add_node("web_worker",          web_worker)
_builder.add_node("fact_extractor",      fact_extractor)
_builder.add_node("validate_fact",       validate_fact)
_builder.add_node("validate_and_split",  validate_and_split)
_builder.add_node("finbert_scorer",      finbert_scorer)
_builder.add_node("quality_gate",        quality_gate)
_builder.add_node("triangulator",        triangulator)
_builder.add_node("contradiction_writer",contradiction_writer)
_builder.add_node("signal_scorer",       signal_scorer)
_builder.add_node("narrative_synthesizer",narrative_synthesizer)
_builder.add_node("watch_list_builder",  watch_list_builder)
_builder.add_node("report_assembler",    report_assembler)

# Main pipeline edges (matching DAG in ARCHITECTURE.md §2)
_builder.add_edge(START,               "query_planner")
_builder.add_conditional_edges("query_planner", _fanout_web_workers)
_builder.add_edge("web_worker",        "fact_extractor")
_builder.add_edge("fact_extractor",    "validate_fact")
_builder.add_edge("validate_fact",     "validate_and_split")
_builder.add_edge("validate_and_split","finbert_scorer")
_builder.add_edge("finbert_scorer",    "quality_gate")

# Conditional edge: quality_gate → expand_queries (loop back) or proceed
_builder.add_conditional_edges(
    "quality_gate",
    _quality_gate_router,
    {
        "expand_queries": "query_planner",   # loop back — round 2 with gap-filling queries
        "proceed":        "triangulator",    # sufficient signal coverage — continue
    },
)

_builder.add_edge("triangulator",          "contradiction_writer")
_builder.add_edge("contradiction_writer",  "signal_scorer")
_builder.add_edge("signal_scorer",         "narrative_synthesizer")
_builder.add_edge("narrative_synthesizer", "watch_list_builder")
_builder.add_edge("watch_list_builder",    "report_assembler")
_builder.add_edge("report_assembler",      END)

# Compile with SQLite checkpointer for pipeline resumption after failure
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
pipeline_graph = _builder.compile(checkpointer=_checkpointer)
