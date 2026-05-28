import type { SignalType } from '@/types'

const SIGNAL_LABELS: Record<SignalType, string> = {
  strategic_messaging: 'Strategic Messaging',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  investor_signal: 'Investor Signal',
  supplier_risk: 'Supplier Risk',
  news_sentiment: 'News Sentiment',
  hiring_momentum: 'Hiring Momentum',
}

const SIGNAL_ORDER: SignalType[] = [
  'strategic_messaging',
  'product_launch',
  'pricing_pressure',
  'investor_signal',
  'supplier_risk',
  'news_sentiment',
]

const SIGNAL_COLORS: Record<SignalType, string> = {
  strategic_messaging: 'bg-blue-500',
  product_launch: 'bg-green-500',
  pricing_pressure: 'bg-amber-500',
  investor_signal: 'bg-indigo-500',
  supplier_risk: 'bg-red-400',
  news_sentiment: 'bg-sky-400',
  hiring_momentum: 'bg-gray-300',
}

interface SignalCoverageProps {
  signalBreakdown: Partial<Record<SignalType, number>>
}

export default function SignalCoverage({ signalBreakdown }: SignalCoverageProps) {
  const maxCount = Math.max(...SIGNAL_ORDER.map(s => signalBreakdown[s] ?? 0), 1)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Signal Coverage</span>
        <span className="text-xs text-gray-400">facts per signal type</span>
      </div>
      <div className="flex flex-col gap-2.5">
        {SIGNAL_ORDER.map(signal => {
          const count = signalBreakdown[signal] ?? 0
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0
          return (
            <div key={signal} className="flex items-center gap-3">
              <span className="text-[11px] text-gray-500 w-40 shrink-0 truncate">
                {SIGNAL_LABELS[signal]}
              </span>
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${SIGNAL_COLORS[signal]}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] tabular-nums text-gray-700 font-medium w-5 text-right">
                {count}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
