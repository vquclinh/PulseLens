import type { SignalType } from '@/types'

const SIGNAL_CHIP_CLS: Record<SignalType, string> = {
  pricing_pressure:   'bg-amber-50 text-amber-700 border-amber-200',
  investor_signal:    'bg-indigo-50 text-indigo-700 border-indigo-200',
  product_launch:     'bg-green-50 text-green-700 border-green-200',
  supplier_risk:      'bg-red-50 text-red-600 border-red-200',
  strategic_messaging:'bg-blue-50 text-blue-700 border-blue-200',
  news_sentiment:     'bg-sky-50 text-sky-700 border-sky-200',
  hiring_momentum:    'bg-gray-100 text-gray-600 border-gray-200',
}

const SIGNAL_LABELS: Record<SignalType, string> = {
  pricing_pressure:   'Pricing',
  investor_signal:    'Investor',
  product_launch:     'Product',
  supplier_risk:      'Supplier Risk',
  strategic_messaging:'Messaging',
  news_sentiment:     'News',
  hiring_momentum:    'Hiring',
}

const TIER_COLORS: Record<number, string> = {
  1: 'bg-blue-100 text-blue-700 border-blue-200',
  2: 'bg-sky-100 text-sky-700 border-sky-200',
  3: 'bg-teal-100 text-teal-700 border-teal-200',
  4: 'bg-gray-100 text-gray-600 border-gray-200',
}

const SENTIMENT_DOT: Record<string, string> = {
  positive: 'bg-green-500',
  negative: 'bg-red-500',
  neutral:  'bg-amber-400',
}

// Minimal interface satisfied by both FactObject (live) and DemoFact (fallback)
export interface DisplayFact {
  fact_id: string
  signal_type: SignalType
  entity: string
  claim?: string
  evidence_quote: string
  source_tier: 1 | 2 | 3 | 4
  sentiment: 'positive' | 'negative' | 'neutral'
  confidence: number
  domain?: string       // present in DemoFact
  source_url?: string   // present in FactObject — domain derived from this
}

interface FactPreviewProps {
  facts: DisplayFact[]
  activeSignal: SignalType | 'all'
  activeCompany: string
  sortMode: 'confidence' | 'tier'
  onSortChange: (sortMode: 'confidence' | 'tier') => void
  isFallback?: boolean
  isLoading?: boolean
}

function deriveDomain(f: DisplayFact): string {
  if (f.domain) return f.domain
  if (f.source_url) {
    try { return new URL(f.source_url).hostname } catch { return f.source_url }
  }
  return 'unknown'
}

export default function FactPreview({
  facts,
  activeSignal,
  activeCompany,
  sortMode,
  onSortChange,
  isFallback = false,
  isLoading = false,
}: FactPreviewProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-gray-950">Featured Insights</h2>
          <p className="text-sm text-gray-500 mt-1">
            Filtered by {activeSignal === 'all' ? 'all signals' : SIGNAL_LABELS[activeSignal]} and {activeCompany === 'all' ? 'all companies' : activeCompany}.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={sortMode}
            onChange={event => onSortChange(event.target.value as 'confidence' | 'tier')}
            className="h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700"
          >
            <option value="confidence">Sort by confidence</option>
            <option value="tier">Sort by source tier</option>
          </select>
          <span className="text-xs text-gray-400 whitespace-nowrap">
          {isFallback ? (
            <span className="text-amber-600">Demo baseline facts</span>
          ) : (
            'Live facts'
          )}
        </span>
        </div>
      </div>
      {isLoading && (
        <div className="bg-white border border-gray-200 rounded-2xl p-5 text-sm text-gray-500">
          Loading live facts from the backend...
        </div>
      )}
      {!isLoading && facts.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-2xl p-6 text-sm text-gray-500">
          No facts match the active filters. Choose All signals or All companies to broaden the evidence set.
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        {facts.map(f => (
          <div key={f.fact_id} className="bg-white border border-gray-200 rounded-2xl p-5 flex flex-col gap-4 shadow-sm">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs font-semibold px-2 py-1 rounded border ${TIER_COLORS[f.source_tier]}`}>
                T{f.source_tier}
              </span>
              <span className="text-sm text-gray-500">{deriveDomain(f)}</span>
              <div className="ml-auto flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full inline-block ${SENTIMENT_DOT[f.sentiment] ?? 'bg-gray-400'}`} />
                <span className={`text-xs font-semibold px-2 py-1 rounded border ${SIGNAL_CHIP_CLS[f.signal_type]}`}>
                  {SIGNAL_LABELS[f.signal_type]}
                </span>
              </div>
            </div>
            {f.claim && (
              <h3 className="text-base font-semibold leading-snug text-gray-950">{f.claim}</h3>
            )}
            <p className="text-sm text-gray-700 leading-relaxed border-l-2 border-blue-200 pl-3 italic">
              "{f.evidence_quote}"
            </p>
            <div className="flex items-center gap-2 pt-1">
              <span className="text-xs text-gray-500">
                {f.entity} · confidence {(f.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="pt-1">
        <button
          type="button"
          className="text-sm font-semibold text-blue-600 hover:text-blue-700"
          onClick={() => window.location.assign('/workspace/evidence')}
        >
          View all evidence →
        </button>
      </div>
    </div>
  )
}
