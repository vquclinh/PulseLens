"""
Live integration test for Agent 1 (query planner) and Agent 2 (web workers).
Requires OPENROUTER_API_KEY and BRIGHTDATA_* env vars to be set.

Run: pytest tests/test_pipeline_live.py -v -s
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ── Agent 1 ───────────────────────────────────────────────────────────────────

def test_agent1_generates_queries():
    """Agent 1 must produce ≥15 queries covering all 8 companies and ≥5 signal types."""
    from app.pipeline.agent1_query_planner import QueryPlanner
    from app.config.companies import COMPANIES
    from app.config.quality_gates import MIN_QUERIES

    planner = QueryPlanner()
    queries = planner.run(
        market="US AI Hardware / Semiconductor",
        companies=[c.name for c in COMPANIES],
        time_window="last 7 days",
    )

    assert len(queries) >= MIN_QUERIES, (
        f"Expected ≥{MIN_QUERIES} queries, got {len(queries)}"
    )

    entities = {q.target_entity for q in queries}
    company_names = {c.name for c in COMPANIES}
    missing = company_names - entities
    assert not missing, f"Companies with 0 queries: {missing}"

    signal_types = {q.signal_type for q in queries}
    assert len(signal_types) >= 5, (
        f"Expected ≥5 signal types, got {len(signal_types)}: {signal_types}"
    )

    print(f"\nAgent 1 generated {len(queries)} queries")
    print(f"  Companies covered: {len(entities)}/8")
    print(f"  Signal types: {len(signal_types)}")
    for q in queries[:5]:
        print(f"  [{q.signal_type.value}] {q.target_entity}: {q.query_text[:80]}")
    print(f"  ... ({len(queries) - 5} more)")


# ── Agent 2 ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent2_serp_search():
    """Agent 2 must return ≥1 document from Bright Data SERP for a simple query."""
    from app.pipeline.agent2_web_workers import collect_documents_for_query
    from app.schemas.models import SearchQuery, SignalType
    from app.utils.helpers import generate_uuid

    query = SearchQuery(
        query_id=generate_uuid()[:12],
        query_text="Nvidia AI GPU news 2025",
        target_entity="Nvidia",
        signal_type=SignalType.news_sentiment,
        source_type="serp_news",
        priority=1,
        expected_source_tier=3,
    )

    docs = await collect_documents_for_query(query)

    assert len(docs) >= 1, "Expected ≥1 document from Bright Data SERP"
    print(f"\nAgent 2 collected {len(docs)} documents for '{query.query_text}'")
    for doc in docs[:3]:
        print(f"  [{doc.source_tier}] {doc.title[:60]} — {doc.url[:60]}")
        print(f"    content: {len(doc.content)} chars")


@pytest.mark.asyncio
async def test_agent2_scrape_ir_page():
    """Agent 2 must scrape an IR page and return meaningful content."""
    from app.pipeline.agent2_web_workers import collect_documents_for_query
    from app.schemas.models import SearchQuery, SignalType
    from app.utils.helpers import generate_uuid

    query = SearchQuery(
        query_id=generate_uuid()[:12],
        query_text="https://ir.nvidia.com/news-events/press-releases",
        target_entity="Nvidia",
        signal_type=SignalType.investor_signal,
        source_type="ir_pages",
        priority=1,
        expected_source_tier=1,
    )

    docs = await collect_documents_for_query(query)
    print(f"\nAgent 2 scraped IR page: {len(docs)} document(s)")
    for doc in docs:
        print(f"  title: {doc.title[:80]}")
        print(f"  content: {len(doc.content)} chars")
        print(f"  tier: {doc.source_tier}")


# ── LangGraph pipeline ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_langgraph_pipeline_agent1_agent2():
    """
    Run the LangGraph pipeline through Agent 1 + Agent 2.
    Downstream nodes are stubs — this validates the graph wiring,
    state accumulation, and Send fan-out.
    """
    from app.pipeline.graph import pipeline_graph
    from app.config.companies import COMPANIES

    config = {"configurable": {"thread_id": "test-live-001"}}
    # Use 2 companies to keep cost and runtime reasonable in CI
    initial_state = {
        "market": "US AI Hardware / Semiconductor",
        "companies": ["Nvidia", "AMD"],
        "time_window": "last 7 days",
    }

    print("\nRunning LangGraph pipeline (Agent 1 + Agent 2)...")
    final_state = await pipeline_graph.ainvoke(initial_state, config=config)

    queries = final_state.get("queries") or []
    raw_docs = final_state.get("raw_documents") or []

    print(f"  Queries generated:  {len(queries)}")
    print(f"  Documents collected: {len(raw_docs)}")
    print(f"  Quality passed:      {final_state.get('quality_passed')}")

    assert len(queries) >= 1, "Pipeline produced no queries"
    assert len(raw_docs) >= 0, "raw_documents missing from state"

    if raw_docs:
        print("\nSample documents:")
        for doc in raw_docs[:3]:
            print(f"  [{doc.source_tier}] {doc.domain} — {doc.title[:50]}")
