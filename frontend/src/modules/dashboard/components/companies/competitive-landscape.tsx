// Competitive landscape — compact gaining/holding/losing position summary across 8 companies
import type { FC } from 'react'
import type { CompanyNarrative } from '@/types/api'
import { normalizeScore } from '@/lib/utils'

interface CompetitiveLandscapeProps {
  narratives: CompanyNarrative[]
}

const CompetitiveLandscape: FC<CompetitiveLandscapeProps> = ({ narratives }) => {
  const gaining = narratives.filter((n) => n.competitive_position === 'gaining')
  const holding = narratives.filter((n) => n.competitive_position === 'holding')
  const losing  = narratives.filter((n) => n.competitive_position === 'losing')

  const sorted = [...narratives].sort((a, b) => b.momentum_score - a.momentum_score)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        Competitive Landscape
      </span>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Gaining', items: gaining, color: 'text-green-600 bg-green-50 border-green-200' },
          { label: 'Holding', items: holding, color: 'text-blue-600 bg-blue-50 border-blue-200' },
          { label: 'Losing',  items: losing,  color: 'text-red-600 bg-red-50 border-red-200' },
        ].map(({ label, items, color }) => (
          <div key={label} className={`rounded-lg border p-3 flex flex-col gap-1.5 ${color}`}>
            <span className="text-[10px] font-semibold uppercase">{label} ({items.length})</span>
            {items.map((n) => (
              <span key={n.ticker} className="text-xs font-medium">{n.company}</span>
            ))}
            {items.length === 0 && <span className="text-xs opacity-50">—</span>}
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-gray-500 font-medium">Score Ranking</span>
        {sorted.map((n) => {
          const pct = normalizeScore(n.momentum_score)
          return (
            <div key={n.ticker} className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold text-gray-700 w-12 shrink-0">{n.ticker}</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    n.momentum_score >= 0.4 ? 'bg-green-500' :
                    n.momentum_score >= 0   ? 'bg-blue-400'  : 'bg-red-400'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] tabular-nums text-gray-500 w-6 text-right">{pct}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default CompetitiveLandscape
