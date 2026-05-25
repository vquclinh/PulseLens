# Pipeline LangGraph StateGraph — nodes, Agent 2 batch collection, quality-gate conditional
# Agent 1 and Agent 2 are implemented; downstream agents are wired as placeholders.
from __future__ import annotations

import logging
import os
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.config.quality_gates import MAX_EXPANSION_ROUNDS
from app.pipeline.agent1_query_planner import QueryPlanner
from app.pipeline.agent2_web_workers import collect_documents, collect_documents_for_query
from app.pipeline.agent3_fact_extractors import extract_facts_from_documents
from app.pipeline.node_validate_and_split import run_safe_verification, validate_facts
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# ── Database path (absolute so it's invariant to cwd) ──────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "pulselens.db"))
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

# ── Node functions ─────────────────────────────────────────────────────────────
# Agent 1 and Agent 2 are implemented; later-stage nodes remain placeholders.

async def query_planner(state: PipelineState) -> dict:
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
    """Agent 2 — Web Collection Workers (Bright Data, internally concurrent batch collection)"""
    query = state.get("agent2_query")
    if query is not None:
        logger.info("node: web_worker query_id=%s", query.query_id)
        return {"raw_documents": await collect_documents_for_query(query)}

    # Fallback path for direct node testing without Send.
    queries = state.get("queries") or []
    logger.info("node: web_worker fallback batch size=%d", len(queries))
    return {"raw_documents": await collect_documents(queries)}


async def fact_extractor(state: PipelineState) -> dict:
    """Agent 3 — Fact Extractors (RASG schema-constrained extraction, parallel fan-out)"""
    documents = state.get("raw_documents") or []
    logger.info("node: fact_extractor documents=%d", len(documents))
    raw_facts = await extract_facts_from_documents(documents)
    logger.info(
        "node: fact_extractor extracted %d raw facts from %d documents",
        len(raw_facts),
        len(documents),
    )
    return {"raw_facts": raw_facts}


async def validate_fact(state: PipelineState) -> dict:
    """Node — validate_fact: evidence_quote verbatim check, confidence filter"""
    raw_facts = state.get("raw_facts") or []
    documents = state.get("raw_documents") or []
    docs_by_id = {doc.doc_id: doc for doc in documents}
    logger.info(
        "node: validate_fact raw_facts=%d documents=%d",
        len(raw_facts),
        len(documents),
    )
    validated = validate_facts(raw_facts, docs_by_id)
    logger.info(
        "node: validate_fact passed=%d failed=%d",
        len(validated),
        len(raw_facts) - len(validated),
    )
    return {"raw_facts": validated}


async def validate_and_split(state: PipelineState) -> dict:
    """Node — SAFE Atomic Verification (arXiv:2403.18802)"""
    validated_facts = state.get("raw_facts") or []
    logger.info("node: validate_and_split validated_facts=%d", len(validated_facts))
    safe_facts = await run_safe_verification(validated_facts)
    logger.info(
        "node: validate_and_split safe_passed=%d safe_failed=%d",
        len(safe_facts),
        len(validated_facts) - len(safe_facts),
    )
    # Agent 4 will replace sentiment fields later; until then these are the
    # SAFE-passed facts available to the quality gate and downstream stubs.
    return {"scored_facts": safe_facts}


async def finbert_scorer(state: PipelineState) -> dict:
    """Agent 4 — FinBERT Scorer (ProsusAI/finbert, batch sentiment)"""
    logger.info("node: finbert_scorer")
    return {}


async def quality_gate(state: PipelineState) -> dict:
    """Node — Quality Gate: checks signal coverage, owns query_expansion_rounds counter"""
    logger.info("node: quality_gate")
    scored_facts = state.get("scored_facts") or []
    expansion_rounds = state.get("query_expansion_rounds", 0)

    # Short-circuit: no scored facts yet (upstream nodes are stubs) → pass
    if not scored_facts:
        return {"quality_passed": True}

    # Real check: signal coverage gate (TODO: tune thresholds with real data)
    covered: set[str] = set()
    for fact in scored_facts:
        signal_type = fact.get("signal_type") if isinstance(fact, dict) else getattr(fact, "signal_type", None)
        if hasattr(signal_type, "value"):
            signal_type = signal_type.value
        if signal_type:
            covered.add(str(signal_type))
    if len(covered) < 4 and expansion_rounds < MAX_EXPANSION_ROUNDS:
        from app.schemas.models import SignalType
        all_signal_types = {st.value for st in SignalType}
        return {
            "quality_passed": False,
            "query_expansion_rounds": expansion_rounds + 1,
            "low_signal_types": sorted(all_signal_types - covered),
        }

    return {"quality_passed": True}


async def triangulator(state: PipelineState) -> dict:
    """Node — M4 Triangulator (ClaimCheck + MiniCheck + FActScore)"""
    logger.info("node: triangulator")
    return {}


async def contradiction_writer(state: PipelineState) -> dict:
    """Agent 5 — Contradiction Writers (parallel fan-out per contradicted pair)"""
    logger.info("node: contradiction_writer")
    return {}


async def signal_scorer(state: PipelineState) -> dict:
    """Node — M5 Signal Scorer (weighted formula: tier × recency × factscore)"""
    logger.info("node: signal_scorer")
    return {}


async def narrative_synthesizer(state: PipelineState) -> dict:
    """Agent 6 — Narrative Synthesizer (STORM multi-perspective, arXiv:2402.14207)"""
    logger.info("node: narrative_synthesizer")
    return {}


async def watch_list_builder(state: PipelineState) -> dict:
    """Agent 7 — Watch List Builder (forward indicators from unresolved signals)"""
    logger.info("node: watch_list_builder")
    return {}


async def report_assembler(state: PipelineState) -> dict:
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

# Main pipeline edges; Agent 2 currently batches internally instead of LangGraph Send fan-out.
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

# TODO: Replace MemorySaver with AsyncSqliteSaver for persistence
# TODO: Revisit LangGraph Send fan-out for M2/M3 once runtime is stable
pipeline_graph = _builder.compile(checkpointer=MemorySaver())
