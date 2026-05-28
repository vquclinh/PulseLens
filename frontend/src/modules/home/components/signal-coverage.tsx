import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { SignalType } from '@/types'
import type { DisplayFact } from './fact-preview'

const SIGNAL_LABELS: Record<SignalType, string> = {
  strategic_messaging: 'Strategic Messaging',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  investor_signal: 'Investor Signal',
  supplier_risk: 'Supplier Risk',
  news_sentiment: 'News Sentiment',
  hiring_momentum: 'Hiring Momentum',
}

const SIGNAL_DESCRIPTIONS: Record<SignalType, string> = {
  strategic_messaging: 'Company positioning, partnerships, roadmap, and market narrative.',
  product_launch: 'New chips, platforms, servers, products, or portfolio expansion.',
  pricing_pressure: 'GPU rental prices, cloud pricing, cost pressure, and margin pressure.',
  investor_signal: 'Earnings, filings, institutional activity, and investor-facing updates.',
  supplier_risk: 'Supply chain, shortage, capacity, vendor, and manufacturing risks.',
  news_sentiment: 'Market sentiment from news and external coverage.',
  hiring_momentum: 'Hiring and talent expansion signals.',
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
  facts: DisplayFact[]
  activeSignal: SignalType | 'all'
  onSignalChange: (signal: SignalType | 'all') => void
  isFallback?: boolean
  isLoading?: boolean
}

export const SIGNAL_LABELS_FULL = SIGNAL_LABELS

export default function SignalCoverage({
  facts,
  activeSignal,
  onSignalChange,
  isFallback = false,
  isLoading = false,
}: SignalCoverageProps) {
  
  const stats = useMemo(() => {
    const s: Partial<Record<SignalType, { count: number, safeCount: number, confSum: number, entities: Record<string, number> }>> = {}
    SIGNAL_ORDER.forEach(sig => {
      s[sig] = { count: 0, safeCount: 0, confSum: 0, entities: {} }
    })
    facts.forEach(f => {
      if (s[f.signal_type]) {
        s[f.signal_type]!.count += 1
        if (f.safe_verified) s[f.signal_type]!.safeCount += 1
        s[f.signal_type]!.confSum += f.confidence
        s[f.signal_type]!.entities[f.entity] = (s[f.signal_type]!.entities[f.entity] || 0) + 1
      }
    })
    return s as Record<SignalType, { count: number, safeCount: number, confSum: number, entities: Record<string, number> }>
  }, [facts])

  const maxCount = Math.max(...SIGNAL_ORDER.map(sig => stats[sig]?.count ?? 0), 1)

  // Details for active signal
  const activeStats = activeSignal !== 'all' ? stats[activeSignal] : null
  const topEntity = activeStats ? Object.entries(activeStats.entities).sort((a, b) => b[1] - a[1])[0]?.[0] : null
  const activeFacts = activeSignal !== 'all' ? facts.filter(f => f.signal_type === activeSignal).sort((a,b) => b.confidence - a.confidence).slice(0, 2) : []

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-950">Signal Radar</h2>
          <p className="text-sm text-gray-500 mt-1">
            Select a signal to preview the evidence behind that market movement.
          </p>
        </div>
        <span className={isFallback ? 'text-xs text-amber-600' : 'text-xs text-gray-400'}>
          {isLoading ? 'loading live facts' : isFallback ? 'fallback sample counts' : 'live market signals'}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.1fr] gap-8">
        {/* Left side: Signal Rows */}
        <div className="flex flex-col gap-3">
          <button
            onClick={() => onSignalChange('all')}
            className={[
              'px-4 py-2 rounded-xl text-sm font-semibold border transition-all text-left',
              activeSignal === 'all'
                ? 'bg-gray-950 text-white border-gray-950 shadow-md'
                : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300 hover:bg-gray-50',
            ].join(' ')}
          >
            All Signals
          </button>

          {SIGNAL_ORDER.map(signal => {
            const st = stats[signal]
            const pct = maxCount > 0 ? (st.count / maxCount) * 100 : 0
            const isActive = activeSignal === signal
            const avgConf = st.count > 0 ? (st.confSum / st.count) * 100 : 0

            return (
              <button
                key={signal}
                onClick={() => onSignalChange(signal)}
                className={[
                  'flex flex-col gap-2 rounded-xl p-3 border transition-all text-left group',
                  isActive 
                    ? 'bg-blue-50/50 border-blue-200 ring-1 ring-blue-200 shadow-sm' 
                    : 'bg-white border-gray-100 hover:border-gray-300 hover:bg-gray-50',
                ].join(' ')}
              >
                <div className="flex items-center justify-between w-full">
                  <span className={`text-sm font-semibold ${isActive ? 'text-blue-900' : 'text-gray-800'}`}>
                    {SIGNAL_LABELS[signal]}
                  </span>
                  <div className="flex items-center gap-2 text-[11px] font-medium text-gray-500">
                    {st.count > 0 && <span>{avgConf.toFixed(0)}% avg conf</span>}
                    <span className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                      {st.count} {st.count === 1 ? 'fact' : 'facts'}
                    </span>
                  </div>
                </div>
                
                <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${SIGNAL_COLORS[signal]}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </button>
            )
          })}
        </div>

        {/* Right side: Detail Panel */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex flex-col h-full min-h-[300px]">
          {activeSignal === 'all' ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-gray-500">
              <div className="w-12 h-12 mb-4 rounded-full bg-slate-200 flex items-center justify-center">
                <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </div>
              <p className="text-sm max-w-[200px]">Select a specific signal on the left to see market movement evidence.</p>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="mb-4">
                <h3 className="text-lg font-bold text-gray-900">{SIGNAL_LABELS[activeSignal]}</h3>
                <p className="text-sm text-gray-600 mt-1">{SIGNAL_DESCRIPTIONS[activeSignal]}</p>
              </div>
              
              <div className="flex items-center gap-4 mb-6 text-xs text-gray-600 font-medium bg-white px-4 py-2.5 rounded-lg border border-gray-100 shadow-sm">
                <div className="flex flex-col">
                  <span className="text-gray-400 text-[10px] uppercase tracking-wider">Facts</span>
                  <span className="text-gray-900 text-sm">{activeStats?.count ?? 0}</span>
                </div>
                <div className="w-px h-8 bg-gray-200" />
                <div className="flex flex-col">
                  <span className="text-gray-400 text-[10px] uppercase tracking-wider">SAFE Verified</span>
                  <span className="text-gray-900 text-sm">{activeStats?.safeCount ?? 0}</span>
                </div>
                <div className="w-px h-8 bg-gray-200" />
                <div className="flex flex-col">
                  <span className="text-gray-400 text-[10px] uppercase tracking-wider">Top Entity</span>
                  <span className="text-gray-900 text-sm truncate max-w-[100px]">{topEntity ?? 'N/A'}</span>
                </div>
              </div>

              <div className="flex-1">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Evidence Snippets</h4>
                {activeFacts.length === 0 ? (
                  <p className="text-sm text-gray-500 italic">No evidence facts for this signal in the latest report.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {activeFacts.map(f => (
                      <div key={f.fact_id} className="text-sm text-gray-700 bg-white border border-gray-100 p-3 rounded-lg shadow-sm border-l-[3px] border-l-blue-400">
                        <p className="line-clamp-2 italic">"{f.evidence_quote}"</p>
                        <span className="block mt-1.5 text-xs text-gray-400 font-medium">{f.entity} · {(f.confidence * 100).toFixed(0)}% conf</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-auto pt-6">
                <Link to="/workspace/signals" className="text-sm font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
                  Open Signal Radar <span aria-hidden="true">&rarr;</span>
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
