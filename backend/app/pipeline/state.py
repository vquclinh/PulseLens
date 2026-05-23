# PipelineState — LangGraph TypedDict shared across all pipeline nodes
from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional

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


class PipelineState(TypedDict):
    # Input
    market: str
    companies: List[str]
    time_window: str

    # Agent 1 output
    queries: List[SearchQuery]

    # Agent 2 output
    raw_documents: List[RawDocument]

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

    # Error accumulation — failed nodes log here, pipeline continues
    errors: List[str]
