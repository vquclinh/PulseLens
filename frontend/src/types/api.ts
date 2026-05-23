// TypeScript types mirroring all backend Pydantic schemas for type-safe API consumption

export type SignalType =
  | 'hiring_momentum'
  | 'product_launch'
  | 'pricing_pressure'
  | 'strategic_messaging'
  | 'investor_signal'
  | 'news_sentiment'
  | 'supplier_risk'

export type PulseStatus =
  | 'heating_up'
  | 'stable'
  | 'cooling_down'
  | 'volatile'
  | 'risk_rising'

export type MomentumLabel =
  | 'strong_positive'
  | 'positive'
  | 'neutral'
  | 'mixed'
  | 'negative'
  | 'elevated_risk'

export interface RawDocument {
  doc_id: string
  url: string
  domain: string
  title: string
  content: string
  published_date: string | null
  fetched_at: string
  source_tier: number
  collection_query: string
  signal_type_hint: string | null
}

export interface FactObject {
  fact_id: string
  doc_id: string
  entity: string
  signal_type: SignalType
  claim: string
  evidence_quote: string
  source_url: string
  source_tier: number
  published_date: string | null
  sentiment: string
  sentiment_score: number
  confidence: number
}

export interface VerifiedClaim {
  claim_id: string
  entity: string
  signal_type: SignalType
  summary: string
  supporting_facts: string[]
  corroboration_count: number
  source_tiers_present: number[]
  weighted_sentiment: number
  recency_score: number
  final_confidence: number
  is_contradicted: boolean
  contradiction_note: string | null
}

export interface AnomalyFlag {
  description: string
  signal_types_involved: string[]
  implication: string
  fact_ids: string[]
}

export interface WatchItem {
  title: string
  rationale: string
  trigger: string
  signals_pointing_there: string[]
  urgency: string
}

export interface CompanyNarrative {
  company: string
  ticker: string
  momentum: MomentumLabel
  momentum_score: number
  narrative: string
  key_events: string[]
  key_drivers: string[]
  competitive_position: string
  supporting_claim_ids: string[]
  evidence_count: number
  price_current: number | null
  price_change_7d_pct: number | null
  signal_lead_days: number | null
}

export interface MarketNarrative {
  narrative_headline: string
  narrative_body: string
  anomalies: AnomalyFlag[]
  watch_list: WatchItem[]
}

export interface CitedStatement {
  text: string
  fact_ids: string[]
}

export interface GroundedBrief {
  what_we_found: CitedStatement[]
  what_we_infer: CitedStatement[]
  strategic_implication: CitedStatement[]
}

export interface SignalSummary {
  signal_type: SignalType
  score: number
  source_count: number
  confidence: number
  narrative: string
  is_contradicted: boolean
}

export interface NewsItem {
  item_id: string
  headline: string
  summary: string
  source_url: string
  domain: string
  source_tier: number
  published_date: string | null
  sentiment: string
  fact_ids: string[]
}

export interface ContradictionFlag {
  entity: string
  signal_type: SignalType
  positive_facts: string[]
  negative_facts: string[]
  note: string
}

export interface MarketPulseReport {
  report_id: string
  market: string
  time_window: string
  generated_at: string
  pulse_score: number
  pulse_status: PulseStatus
  pulse_confidence: number
  trend_vs_previous: number | null
  top_signals: SignalSummary[]
  company_narratives: CompanyNarrative[]
  news_items: NewsItem[]
  market_narrative: MarketNarrative
  contradictions: ContradictionFlag[]
  grounded_brief: GroundedBrief
  evidence_count: number
  source_count: number
  signal_breakdown: Record<string, number>
}

export interface StockContext {
  company: string
  ticker: string
  price_current: number | null
  price_7d_change_pct: number | null
  price_7d_high: number | null
  price_7d_low: number | null
  signal_detected_date: string | null
  price_move_date: string | null
  signal_lead_days: number | null
  lead_time_note: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  cited_fact_ids: string[] | null
}

export interface ChatRequest {
  query: string
  report_id: string
  history: ChatMessage[] | null
}

export interface ChatResponse {
  response: string
  cited_facts: FactObject[]
  session_id: string
}
