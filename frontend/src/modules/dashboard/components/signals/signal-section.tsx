// Collapsible signal section — header with score bar, narrative, evidence cards, contradiction note
import { FC, useState } from 'react'
import type { SignalSummary, VerifiedClaim } from '@/types/api'
import EvidenceCard from './evidence-card'
import { normalizeScore } from '@/lib/utils'

interface SignalSectionProps {
  signal: SignalSummary
  claims: VerifiedClaim[]
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

const SignalSection: FC<SignalSectionProps> = ({ signal, claims }) => {
  const [open, setOpen] = useState(false)
  const pct = normalizeScore(signal.score)
  const label = SIGNAL_LABELS[signal.signal_type] ?? signal.signal_type

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-sm font-semibold text-gray-900">{label}</span>
            {signal.is_contradicted && (
              <span className="text-[10px] font-semibold bg-red-100 text-red-700 border border-red-200 rounded px-1.5 py-0.5">
                Contradicted
              </span>
            )}
            <span className="ml-auto text-xs text-gray-400">{signal.source_count} sources</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${signal.score >= 0 ? 'bg-blue-500' : 'bg-red-400'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-[11px] tabular-nums text-gray-600 w-6 text-right">{pct}</span>
          </div>
        </div>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-gray-100 p-4 flex flex-col gap-3">
          <p className="text-sm text-gray-600">{signal.narrative}</p>
          {claims.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Evidence</span>
              {claims.slice(0, 5).map((c) => (
                <div key={c.claim_id} className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700">
                  <p>{c.summary}</p>
                  <div className="mt-1.5 flex items-center gap-2 text-gray-400">
                    <span>{c.corroboration_count} corroborations</span>
                    <span>·</span>
                    <span>confidence {c.final_confidence.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SignalSection
