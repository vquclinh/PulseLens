import type { MomentumLabel, SignalType } from '@/types'

export const DEMO_REPORT_ID = 'report_e68e7289fc30'
export const DEMO_DATE = '2026-05-28'

export const DEMO_PULSE = {
  score: 52.7,
  status: 'risk_rising' as const,
  confidence: 0.611,
}

export const DEMO_COUNTS = {
  evidenceCount: 67,
  sourceCount: 23,
  verifiedClaimsCount: 10,
}

export const DEMO_SIGNAL_BREAKDOWN: Record<SignalType, number> = {
  strategic_messaging: 17,
  product_launch: 16,
  pricing_pressure: 14,
  investor_signal: 12,
  supplier_risk: 7,
  news_sentiment: 1,
  hiring_momentum: 0,
}

export const DEMO_COMPANIES: Array<{
  company: string
  ticker: string
  momentum: MomentumLabel
  key_drivers: string[]
}> = [
  {
    company: 'AMD',
    ticker: 'AMD',
    momentum: 'positive',
    key_drivers: ['TSMC 2nm EPYC ramp', '$10B Taiwan investment', 'Data center share gains'],
  },
  {
    company: 'Nvidia',
    ticker: 'NVDA',
    momentum: 'strong_positive',
    key_drivers: ['Blackwell B200/B300 demand', 'AI inference leadership', 'Hyperscaler buildout'],
  },
  {
    company: 'Supermicro',
    ticker: 'SMCI',
    momentum: 'elevated_risk',
    key_drivers: ['Supply chain expansion', 'IR compliance work', 'Rack-scale GPU systems'],
  },
]

export interface DemoFact {
  fact_id: string
  signal_type: SignalType
  entity: string
  claim: string
  evidence_quote: string
  domain: string
  source_tier: 1 | 2 | 3 | 4
  confidence: number
  sentiment: 'positive' | 'negative' | 'neutral'
}

export const DEMO_FACTS: DemoFact[] = [
  {
    fact_id: 'demo_f1',
    signal_type: 'pricing_pressure',
    entity: 'market',
    claim: 'CoreWeave B200 on-demand GPU instances priced at $68.80/hr',
    evidence_quote: 'B200 On-demand $68.80/hr',
    domain: 'coreweave.com',
    source_tier: 2,
    confidence: 0.95,
    sentiment: 'neutral',
  },
  {
    fact_id: 'demo_f2',
    signal_type: 'investor_signal',
    entity: 'AMD',
    claim: 'AMD committed $10 billion investment in Taiwan semiconductor manufacturing',
    evidence_quote: '$10 billion investment commitment in Taiwan',
    domain: 'ir.amd.com',
    source_tier: 1,
    confidence: 0.94,
    sentiment: 'positive',
  },
  {
    fact_id: 'demo_f3',
    signal_type: 'product_launch',
    entity: 'AMD',
    claim: 'AMD EPYC processors ramping on TSMC 2nm process node',
    evidence_quote: 'TSMC 2nm production ramp for next-generation EPYC processors',
    domain: 'ir.amd.com',
    source_tier: 1,
    confidence: 0.91,
    sentiment: 'positive',
  },
  {
    fact_id: 'demo_f4',
    signal_type: 'supplier_risk',
    entity: 'Supermicro',
    claim: 'Supermicro expanding supply chain capacity for AI infrastructure demand',
    evidence_quote: 'expanding our supply chain capacity to support growing AI infrastructure demand',
    domain: 'ir.supermicro.com',
    source_tier: 1,
    confidence: 0.88,
    sentiment: 'positive',
  },
]
