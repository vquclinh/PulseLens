# All Pydantic v2 data models — RawDocument, FactObject, VerifiedClaim, MarketPulseReport, etc.
from __future__ import annotations
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel
from enum import Enum


class SignalType(str, Enum):
    hiring_momentum = "hiring_momentum"
    product_launch = "product_launch"
    pricing_pressure = "pricing_pressure"
    strategic_messaging = "strategic_messaging"
    investor_signal = "investor_signal"
    news_sentiment = "news_sentiment"
    supplier_risk = "supplier_risk"


class PulseStatus(str, Enum):
    heating_up = "heating_up"
    stable = "stable"
    cooling_down = "cooling_down"
    volatile = "volatile"
    risk_rising = "risk_rising"


class MomentumLabel(str, Enum):
    strong_positive = "strong_positive"
    positive = "positive"
    neutral = "neutral"
    mixed = "mixed"
    negative = "negative"
    elevated_risk = "elevated_risk"


class RawDocument(BaseModel):
    doc_id: str
    url: str
    domain: str
    title: str
    content: str
    published_date: Optional[str]
    fetched_at: str
    source_tier: Literal[1, 2, 3, 4]
    collection_query: str
    signal_type_hint: Optional[SignalType]


class FactObject(BaseModel):
    fact_id: str
    doc_id: str
    entity: str
    signal_type: SignalType
    claim: str
    evidence_quote: str
    source_url: str
    source_tier: Literal[1, 2, 3, 4]
    published_date: Optional[str]
    sentiment: Literal["positive", "negative", "neutral"]
    sentiment_score: float
    confidence: float
    atomic_claims: Optional[List[str]] = None   # SAFE-verified atomic sub-claims
    safe_verified: bool = False                  # True after SAFE atomic verification passes


class VerifiedClaim(BaseModel):
    claim_id: str
    entity: str
    signal_type: SignalType
    summary: str
    supporting_facts: List[str]
    corroboration_count: int
    source_tiers_present: List[int]
    weighted_sentiment: float
    recency_score: float
    final_confidence: float
    factscore: float = 0.0              # FActScore atomic precision (arXiv:2305.14251)
    is_contradicted: bool
    contradiction_note: Optional[str]


class AnomalyFlag(BaseModel):
    description: str
    signal_types_involved: List[SignalType]
    implication: str
    fact_ids: List[str]


class WatchItem(BaseModel):
    title: str
    rationale: str
    trigger: str
    signals_pointing_there: List[str]
    urgency: Literal["this_week", "next_2_weeks", "this_month"]


class CompanyNarrative(BaseModel):
    company: str
    ticker: str
    momentum: MomentumLabel
    momentum_score: int
    narrative: str
    key_events: List[str]
    key_drivers: List[str]
    competitive_position: Literal["gaining", "holding", "losing"]
    supporting_claim_ids: List[str]
    evidence_count: int
    price_current: Optional[float]
    price_change_7d_pct: Optional[float]
    signal_lead_days: Optional[int]


class MarketNarrative(BaseModel):
    narrative_headline: str
    narrative_body: str
    anomalies: List[AnomalyFlag]
    watch_list: List[WatchItem]


class CitedStatement(BaseModel):
    text: str
    fact_ids: List[str]


class GroundedBrief(BaseModel):
    what_we_found: List[CitedStatement]
    what_we_infer: List[CitedStatement]
    strategic_implication: str


class SignalSummary(BaseModel):
    signal_type: SignalType
    score: float
    source_count: int
    confidence: float
    narrative: str
    is_contradicted: bool


class NewsItem(BaseModel):
    item_id: str
    headline: str
    summary: str
    source_url: str
    domain: str
    source_tier: int
    published_date: Optional[str]
    sentiment: str
    fact_ids: List[str]


class ContradictionFlag(BaseModel):
    entity: str
    signal_type: SignalType
    positive_facts: List[str]
    negative_facts: List[str]
    note: str


class MarketPulseReport(BaseModel):
    report_id: str
    market: str
    time_window: str
    generated_at: str
    pulse_score: float
    pulse_status: PulseStatus
    pulse_confidence: float
    trend_vs_previous: Optional[float]
    top_signals: List[SignalSummary]
    company_narratives: List[CompanyNarrative]
    news_items: List[NewsItem]
    market_narrative: MarketNarrative
    contradictions: List[ContradictionFlag]
    grounded_brief: GroundedBrief
    evidence_count: int
    source_count: int
    signal_breakdown: Dict[str, float]


class StockContext(BaseModel):
    company: str
    ticker: str
    price_current: Optional[float]
    price_7d_change_pct: Optional[float]
    price_7d_high: Optional[float]
    price_7d_low: Optional[float]
    signal_detected_date: Optional[str]
    price_move_date: Optional[str]
    signal_lead_days: Optional[int]
    lead_time_note: Optional[str]


class SearchQuery(BaseModel):
    query_id: str
    query_text: str
    target_entity: str
    signal_type: SignalType
    source_type: str
    priority: int
    expected_source_tier: int


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    cited_fact_ids: Optional[List[str]]


class ChatRequest(BaseModel):
    query: str
    report_id: str
    session_id: Optional[str] = None
    history: Optional[List[ChatMessage]]


class ChatResponse(BaseModel):
    response: str
    cited_facts: List[FactObject]
    session_id: str
