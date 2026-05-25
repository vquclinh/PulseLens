// Contradiction alerts — one alert box per conflicting signal pair with both sides shown
import type { FC } from 'react'
import type { ContradictionFlag } from '@/types/api'
import FactIdChip from '@/shared/components/fact-id-chip'

interface ContradictionAlertsProps {
  contradictions: ContradictionFlag[]
}

const SIGNAL_LABELS: Record<string, string> = {
  hiring_momentum: 'Hiring Momentum',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  strategic_messaging: 'Strategic Messaging',
  investor_signal: 'Investor Signal',
  news_sentiment: 'News Sentiment',
  supplier_risk: 'Supplier Risk',
}

const ContradictionAlerts: FC<ContradictionAlertsProps> = ({ contradictions }) => {
  if (!contradictions.length) return null

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-semibold text-red-600 uppercase tracking-wide">Contradictions Detected</span>
      {contradictions.map((c, i) => (
        <div key={i} className="bg-red-50 border border-red-200 rounded-xl p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-red-800">{c.entity}</span>
            <span className="text-xs text-red-500">·</span>
            <span className="text-xs text-red-600">{SIGNAL_LABELS[c.signal_type] ?? c.signal_type}</span>
          </div>
          <p className="text-xs text-red-700">{c.note}</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-[10px] font-semibold text-green-600 uppercase">Supporting</span>
              <div className="flex gap-1 flex-wrap mt-1">
                {c.positive_facts.map((fid) => <FactIdChip key={fid} factId={fid} />)}
              </div>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-red-600 uppercase">Against</span>
              <div className="flex gap-1 flex-wrap mt-1">
                {c.negative_facts.map((fid) => <FactIdChip key={fid} factId={fid} />)}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default ContradictionAlerts
