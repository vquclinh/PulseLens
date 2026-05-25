// Market narrative section (Layer 3) — headline, body with inline fact citations, anomaly flags
import type { FC } from 'react'
import type { MarketNarrative } from '@/types/api'
import FactIdChip from '@/shared/components/fact-id-chip'

interface MarketNarrativeSectionProps {
  narrative: MarketNarrative
}

const MarketNarrativeSection: FC<MarketNarrativeSectionProps> = ({ narrative }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
      <div>
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Market Narrative</span>
        <h2 className="mt-1 text-base font-semibold text-gray-900">{narrative.narrative_headline}</h2>
      </div>

      <p className="text-sm text-gray-700 leading-relaxed">{narrative.narrative_body}</p>

      {narrative.anomalies.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-amber-600 uppercase tracking-wide">Anomaly Flags</span>
          {narrative.anomalies.map((a, i) => (
            <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex flex-col gap-1.5">
              <p className="text-xs text-amber-800 font-medium">{a.description}</p>
              <p className="text-xs text-amber-700">{a.implication}</p>
              <div className="flex gap-1.5 flex-wrap pt-0.5">
                {a.fact_ids.map((fid) => (
                  <FactIdChip key={fid} factId={fid} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default MarketNarrativeSection
