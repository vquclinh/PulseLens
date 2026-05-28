import type { SignalType } from '@/types'
import type { DemoFact } from '../lib/demo-baseline'

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

interface FactPreviewProps {
  facts: DemoFact[]
  reportId: string
}

export default function FactPreview({ facts, reportId }: FactPreviewProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Featured Insights</h2>
        <span className="text-xs text-gray-400">
          Sample facts · <span className="font-mono">{reportId}</span>
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {facts.map(f => (
          <div key={f.fact_id} className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${TIER_COLORS[f.source_tier]}`}>
                T{f.source_tier}
              </span>
              <span className="text-xs text-gray-400">{f.domain}</span>
              <div className="ml-auto flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full inline-block ${SENTIMENT_DOT[f.sentiment] ?? 'bg-gray-400'}`} />
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${SIGNAL_CHIP_CLS[f.signal_type]}`}>
                  {SIGNAL_LABELS[f.signal_type]}
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-700 leading-relaxed border-l-2 border-gray-200 pl-2.5 italic">
              "{f.evidence_quote}"
            </p>
            <div className="flex items-center gap-2 pt-0.5">
              <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                [{f.fact_id}]
              </span>
              <span className="text-[10px] text-gray-400">
                {f.entity} · confidence {f.confidence.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
