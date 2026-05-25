// Signal breakdown bars — one horizontal bar per signal type showing score and weight
import type { FC } from 'react'
import type { SignalSummary } from '@/types/api'
import { normalizeScore } from '@/lib/utils'

interface SignalBreakdownProps {
  signals: SignalSummary[]
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

const SignalBreakdown: FC<SignalBreakdownProps> = ({ signals }) => {
  if (!signals.length) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Signal Breakdown</span>
      <div className="flex flex-col gap-2">
        {signals.map((s) => {
          const pct = normalizeScore(s.score)
          const isPositive = s.score >= 0
          return (
            <div key={s.signal_type} className="flex items-center gap-2">
              <span className="text-[11px] text-gray-500 w-36 shrink-0 truncate">
                {SIGNAL_LABELS[s.signal_type] ?? s.signal_type}
              </span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isPositive ? 'bg-blue-500' : 'bg-red-400'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] tabular-nums text-gray-600 w-6 text-right">{pct}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default SignalBreakdown
