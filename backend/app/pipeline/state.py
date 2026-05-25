# PipelineState — LangGraph TypedDict shared across all pipeline nodes
from __future__ import annotations

import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional

from app.schemas.models import (
    SearchQuery,
    RawDocument,
    FactObject,
    VerifiedClaim,
    ContradictionFlag,
    CompanyNarrative,
    MarketNarrative,
    MarketPulseReport,
)


class PipelineState(TypedDict, total=False):
    # Input
    market: str
    companies: List[str]
    time_window: str

    # Agent 1 output
    queries: List[SearchQuery]
    pending_queries: List[SearchQuery]
    query_planner_audit: Dict[str, Any]

    # Agent 2 output
    agent2_query: Optional[SearchQuery]     # optional single-query payload for direct Agent 2 tests
    raw_documents: Annotated[List[RawDocument], operator.add]
    web_collection_audit: Dict[str, Any]
    fetch_error_summary: Dict[str, Any]

    # Agent 3 output (pre-validation)
    raw_facts: List[FactObject]

    # After SAFE + FinBERT scoring
    scored_facts: List[FactObject]

    # After M4 triangulation
    verified_claims: List[VerifiedClaim]
    contradictions: List[ContradictionFlag]

    # After M5 signal scoring
    signal_scores: Dict[str, Any]          # keys: pulse_score, pulse_status, pulse_confidence, breakdown
    company_narratives: List[CompanyNarrative]

    # After Agent 6
    market_narrative: Optional[MarketNarrative]

    # Final output
    report: Optional[MarketPulseReport]

    # Quality gate control
    query_expansion_rounds: int            # incremented each time quality gate loops back
    low_signal_types: List[str]            # signal types under-covered — injected into Agent 1 on re-run
    quality_passed: bool
    quality_status: str
    quality_reasons: List[str]
    covered_signal_types: List[str]
    missing_signal_types: List[str]
    company_coverage: float
    zero_doc_query_rate: float
    fetch_error_rate: float
    source_count: int
    fact_count: int

    # Error accumulation — failed nodes log here, pipeline continues
    errors: List[str]
