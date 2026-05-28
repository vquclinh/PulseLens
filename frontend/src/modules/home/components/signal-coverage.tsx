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
  signalFactCounts: Partial<Record<SignalType, number>>
  activeSignal: SignalType | 'all'
  onSignalChange: (signal: SignalType | 'all') => void
  isFallback?: boolean
  isLoading?: boolean
}

export const SIGNAL_LABELS_FULL = SIGNAL_LABELS

export default function SignalCoverage({
  signalFactCounts,
  activeSignal,
  onSignalChange,
  isFallback = false,
  isLoading = false,
}: SignalCoverageProps) {
  const maxCount = Math.max(...SIGNAL_ORDER.map(s => signalFactCounts[s] ?? 0), 1)
  const strongest = SIGNAL_ORDER.reduce(
    (best, signal) => (signalFactCounts[signal] ?? 0) > (signalFactCounts[best] ?? 0) ? signal : best,
    SIGNAL_ORDER[0],
  )
  const strongestCount = signalFactCounts[strongest] ?? 0

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-950">Signal Radar</h2>
          <p className="text-sm text-gray-500 mt-1">
            Strongest signal:{' '}
            <span className="font-medium text-gray-800">
              {strongestCount > 0 ? SIGNAL_LABELS[strongest] : 'waiting for facts'}
            </span>
          </p>
        </div>
        <span className={isFallback ? 'text-xs text-amber-600' : 'text-xs text-gray-400'}>
          {isLoading ? 'loading live facts' : isFallback ? 'fallback sample counts' : 'facts per signal type'}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onSignalChange('all')}
          className={[
            'px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
            activeSignal === 'all'
              ? 'bg-gray-950 text-white border-gray-950'
              : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
          ].join(' ')}
        >
          All
        </button>
        {SIGNAL_ORDER.map(signal => (
          <button
            key={signal}
            onClick={() => onSignalChange(signal)}
            className={[
              'px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
              activeSignal === signal
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
            ].join(' ')}
          >
            {SIGNAL_LABELS[signal]} · {signalFactCounts[signal] ?? 0}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {SIGNAL_ORDER.map(signal => {
          const count = signalFactCounts[signal] ?? 0
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0
          const isActive = activeSignal === signal
          return (
            <button
              key={signal}
              onClick={() => onSignalChange(signal)}
              className={[
                'flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors text-left',
                isActive ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50',
              ].join(' ')}
            >
              <span className="text-sm text-gray-600 w-44 shrink-0 truncate">
                {SIGNAL_LABELS[signal]}
              </span>
              <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${SIGNAL_COLORS[signal]}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-sm tabular-nums text-gray-800 font-semibold w-8 text-right">
                {count}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
