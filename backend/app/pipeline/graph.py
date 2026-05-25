# Pipeline LangGraph StateGraph — nodes, quality-gate conditional, full DAG
# Implemented: Agent 1–7, validate_fact, SAFE, quality_gate, M4 triangulator, M5 signal scorer, company narratives, report assembler
from __future__ import annotations

import logging
import os
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.pipeline.agent1_query_planner import QueryPlanner
from app.pipeline.agent2_web_workers import collect_documents, collect_documents_for_query
from app.pipeline.agent3_fact_extractors import extract_facts_from_documents
from app.pipeline.agent4_finbert_scorer import run_finbert_scorer
from app.pipeline.node_quality_gate import quality_gate_router, run_quality_gate
from app.pipeline.agent5_contradiction_writer import write_contradiction_notes
from app.pipeline.agent6_narrative_synthesizer import run_narrative_synthesizer
from app.pipeline.agent7_watch_list_builder import run_watch_list_builder
from app.pipeline.node_company_narratives import build_company_narratives
from app.pipeline.node_report_assembler import report_assembler as run_report_assembler
from app.pipeline.node_signal_scorer import run_signal_scorer
from app.pipeline.node_triangulator import triangulate
from app.pipeline.node_validate_and_split import run_safe_verification, validate_facts
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# ── Database path (absolute so it's invariant to cwd) ──────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "pulselens.db"))
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)


def _merge_web_audit(previous: dict | None, current: dict | None) -> dict:
    previous = previous or {}
    current = current or {}
    prev_queries = list(previous.get("queries") or [])
    cur_queries = list(current.get("queries") or [])
    merged_queries = prev_queries + cur_queries
    return {
        "query_count": len(merged_queries) or int(previous.get("query_count") or 0) + int(current.get("query_count") or 0),
        "queries": merged_queries,
        "accepted_doc_count": int(previous.get("accepted_doc_count") or 0) + int(current.get("accepted_doc_count") or 0),
        "failed_query_count": int(previous.get("failed_query_count") or 0) + int(current.get("failed_query_count") or 0),
        "zero_doc_query_count": int(previous.get("zero_doc_query_count") or 0) + int(current.get("zero_doc_query_count") or 0),
        "low_quality_discard_count": int(previous.get("low_quality_discard_count") or 0) + int(current.get("low_quality_discard_count") or 0),
    }


def _merge_fetch_summary(previous: dict | None, current: dict | None) -> dict:
    previous = previous or {}
    current = current or {}
    merged_domains: dict[str, int] = {}
    merged_reasons: dict[str, int] = {}
    for source, target in (
        (previous.get("failure_count_by_domain") or {}, merged_domains),
        (current.get("failure_count_by_domain") or {}, merged_domains),
        (previous.get("failure_count_by_reason") or {}, merged_reasons),
        (current.get("failure_count_by_reason") or {}, merged_reasons),
    ):
        for key, value in dict(source).items():
            target[str(key)] = target.get(str(key), 0) + int(value)
    return {
        "total_fetch_attempts": int(previous.get("total_fetch_attempts") or 0) + int(current.get("total_fetch_attempts") or 0),
        "successful_fetches": int(previous.get("successful_fetches") or 0) + int(current.get("successful_fetches") or 0),
        "failed_fetches": int(previous.get("failed_fetches") or 0) + int(current.get("failed_fetches") or 0),
        "permanent_failures": int(previous.get("permanent_failures") or 0) + int(current.get("permanent_failures") or 0),
        "failure_count_by_domain": dict(sorted(merged_domains.items(), key=lambda item: item[1], reverse=True)),
        "failure_count_by_reason": dict(sorted(merged_reasons.items(), key=lambda item: item[1], reverse=True)),
    }

# ── Node functions ─────────────────────────────────────────────────────────────

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
    round_audit = dict(planner.last_query_telemetry)
    round_audit["expansion_round"] = expansion_round
    previous_audit = state.get("query_planner_audit") or {}
    audit_history = list(previous_audit.get("rounds") or []) if isinstance(previous_audit, dict) else []
    combined_audit = {**round_audit, "rounds": audit_history + [round_audit]}
    return {
        "queries": existing + queries,
        "pending_queries": queries,
        "query_planner_audit": combined_audit,
    }   # expansion counter owned by quality_gate


async def web_worker(state: PipelineState) -> dict:
    """Agent 2 — Web Collection Workers (Bright Data, internally concurrent batch collection)"""
    query = state.get("agent2_query")
    if query is not None:
        logger.info("node: web_worker query_id=%s", query.query_id)
        docs = await collect_documents_for_query(query)
        from app.pipeline.agent2_web_workers import get_last_collection_audit, get_last_fetch_error_summary

        return {
            "raw_documents": docs,
            "web_collection_audit": _merge_web_audit(state.get("web_collection_audit"), get_last_collection_audit()),
            "fetch_error_summary": _merge_fetch_summary(state.get("fetch_error_summary"), get_last_fetch_error_summary()),
        }

    # Fallback path for direct node testing without Send.
    queries = state.get("pending_queries") or state.get("queries") or []
    logger.info("node: web_worker fallback batch size=%d", len(queries))
    docs = await collect_documents(queries)
    from app.pipeline.agent2_web_workers import get_last_collection_audit, get_last_fetch_error_summary

    return {
        "raw_documents": docs,
        "web_collection_audit": _merge_web_audit(state.get("web_collection_audit"), get_last_collection_audit()),
        "fetch_error_summary": _merge_fetch_summary(state.get("fetch_error_summary"), get_last_fetch_error_summary()),
    }


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
    return {"scored_facts": safe_facts}


async def finbert_scorer(state: PipelineState) -> dict:
    """Agent 4 — FinBERT Scorer (configured HuggingFace model, batch sentiment)"""
    safe_facts = state.get("scored_facts") or []
    logger.info("node: finbert_scorer facts=%d", len(safe_facts))
    scored, errors = await run_finbert_scorer(safe_facts)
    logger.info("node: finbert_scorer completed %d facts scored errors=%d", len(scored), len(errors))
    result: dict = {"scored_facts": scored}
    if errors:
        result["errors"] = list(state.get("errors") or []) + errors
    return result


async def quality_gate(state: PipelineState) -> dict:
    """Node — Quality Gate: fact count + signal coverage, delegates to node_quality_gate"""
    return run_quality_gate(state)


async def triangulator(state: PipelineState) -> dict:
    """Node — M4 Triangulator (ClaimCheck + MiniCheck + FActScore)"""
    scored_facts = state.get("scored_facts") or []
    logger.info("node: triangulator facts=%d", len(scored_facts))
    verified_claims, contradiction_flags = triangulate(scored_facts)
    logger.info(
        "node: triangulator verified_claims=%d contradictions=%d",
        len(verified_claims), len(contradiction_flags),
    )
    return {"verified_claims": verified_claims, "contradictions": contradiction_flags}


async def contradiction_writer(state: PipelineState) -> dict:
    """Agent 5 — Contradiction Writers (parallel fan-out per contradicted pair)"""
    flags = state.get("contradictions") or []
    scored_facts = state.get("scored_facts") or []
    verified_claims = state.get("verified_claims") or []
    logger.info("node: contradiction_writer flags=%d", len(flags))
    updated_flags, updated_claims = await write_contradiction_notes(flags, scored_facts, verified_claims)
    logger.info("node: contradiction_writer wrote %d notes", len(updated_flags))
    return {"contradictions": updated_flags, "verified_claims": updated_claims}


async def signal_scorer(state: PipelineState) -> dict:
    """Node — M5 Signal Scorer (weighted formula: tier × recency × factscore)"""
    verified_claims = state.get("verified_claims") or []
    logger.info("node: signal_scorer claims=%d", len(verified_claims))
    scores = run_signal_scorer(verified_claims)
    logger.info(
        "node: signal_scorer pulse_score=%.1f status=%s",
        scores["pulse_score"], scores["pulse_status"].value,
    )
    return {"signal_scores": scores}


async def company_narratives(state: PipelineState) -> dict:
    """Node — Company Narratives: Layer 2 company cards for dashboard tabs"""
    verified_claims = state.get("verified_claims") or []
    signal_scores = state.get("signal_scores") or {}
    companies = state.get("companies") or [company.name for company in COMPANIES]
    logger.info(
        "node: company_narratives companies=%d claims=%d",
        len(companies),
        len(verified_claims),
    )
    narratives = await build_company_narratives(verified_claims, signal_scores, companies)
    logger.info("node: company_narratives built=%d", len(narratives))
    return {"company_narratives": narratives}


async def narrative_synthesizer(state: PipelineState) -> dict:
    """Agent 6 — Narrative Synthesizer (STORM multi-perspective, arXiv:2402.14207)"""
    verified_claims = state.get("verified_claims") or []
    signal_scores = state.get("signal_scores") or {}
    narratives = state.get("company_narratives") or []
    logger.info("node: narrative_synthesizer claims=%d", len(verified_claims))
    narrative = await run_narrative_synthesizer(verified_claims, signal_scores, narratives)
    logger.info(
        "node: narrative_synthesizer headline=%r anomalies=%d",
        narrative.narrative_headline[:80],
        len(narrative.anomalies),
    )
    return {"market_narrative": narrative}


async def watch_list_builder(state: PipelineState) -> dict:
    """Agent 7 — Watch List Builder (forward indicators from unresolved signals)"""
    narrative = state.get("market_narrative")
    verified_claims = state.get("verified_claims") or []
    logger.info("node: watch_list_builder claims=%d", len(verified_claims))
    updated_narrative = await run_watch_list_builder(narrative, verified_claims)
    logger.info("node: watch_list_builder items=%d", len(updated_narrative.watch_list))
    return {"market_narrative": updated_narrative}


async def report_assembler(state: PipelineState) -> dict:
    """Node — Report Assembler: assembles MarketPulseReport, saves to SQLite"""
    logger.info("node: report_assembler")
    result = await run_report_assembler(state)
    report = result.get("report")
    if report is not None:
        logger.info("node: report_assembler saved report_id=%s", report.report_id)
    return result


# ── Quality gate router ────────────────────────────────────────────────────────
# Real routing logic lives in node_quality_gate.py; imported as quality_gate_router.


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
_builder.add_node("company_narratives",  company_narratives)
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
    quality_gate_router,
    {
        "expand_queries": "query_planner",   # loop back — round 2 with gap-filling queries
        "proceed":        "triangulator",    # sufficient signal coverage — continue
    },
)

_builder.add_edge("triangulator",          "contradiction_writer")
_builder.add_edge("contradiction_writer",  "signal_scorer")
_builder.add_edge("signal_scorer",         "company_narratives")
_builder.add_edge("company_narratives",    "narrative_synthesizer")
_builder.add_edge("narrative_synthesizer", "watch_list_builder")
_builder.add_edge("watch_list_builder",    "report_assembler")
_builder.add_edge("report_assembler",      END)

# TODO: Replace MemorySaver with AsyncSqliteSaver for persistence
# TODO: Revisit LangGraph Send fan-out for M2/M3 once runtime is stable
pipeline_graph = _builder.compile(checkpointer=MemorySaver())
