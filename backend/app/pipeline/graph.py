# Pipeline LangGraph StateGraph — all nodes, edges, quality-gate conditional, SQLite checkpointer
# Node implementations are placeholders; real agents wired in subsequent tasks.
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# ── Database path (absolute so it's invariant to cwd) ──────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "pulselens.db"))
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

# ── Placeholder node functions ─────────────────────────────────────────────────
# Each returns an empty dict (no state changes) until wired to a real agent.

def query_planner(state: PipelineState) -> dict:
    """Agent 1 — Query Planner (Step-Back + Multi-HyDE)"""
    logger.info("node: query_planner")
    return {}


def web_worker(state: PipelineState) -> dict:
    """Agent 2 — Web Collection Workers (Bright Data, parallel fan-out via Send)"""
    logger.info("node: web_worker")
    return {}


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
    """Node — Quality Gate: checks fact count and signal coverage, updates control fields"""
    logger.info("node: quality_gate")
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
_builder.add_edge("query_planner",     "web_worker")
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
