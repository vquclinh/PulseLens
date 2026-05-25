// Company card — initial circle, name, ticker, momentum badge, score bar, narrative, stock line
import type { FC } from 'react'
import type { CompanyNarrative } from '@/types/api'
import MomentumBadge from '@/shared/components/momentum-badge'
import { normalizeScore, formatPct } from '@/lib/utils'

interface CompanyCardProps {
  narrative: CompanyNarrative
}

const POSITION_STYLES: Record<string, string> = {
  gaining: 'text-green-600 bg-green-50',
  holding: 'text-blue-600 bg-blue-50',
  losing:  'text-red-600 bg-red-50',
}

const CompanyCard: FC<CompanyCardProps> = ({ narrative }) => {
  const pct = normalizeScore(narrative.momentum_score)
  const initials = narrative.company.slice(0, 2).toUpperCase()
  const posStyle = POSITION_STYLES[narrative.competitive_position] ?? POSITION_STYLES.holding

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
          <span className="text-xs font-bold text-blue-700">{initials}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900">{narrative.company}</span>
            <span className="text-xs font-mono text-gray-500">{narrative.ticker}</span>
            <div className="ml-auto">
              <MomentumBadge momentum={narrative.momentum} />
            </div>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${posStyle}`}>
              {narrative.competitive_position}
            </span>
            <span className="text-[10px] text-gray-400">{narrative.evidence_count} facts</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] tabular-nums text-gray-600 w-6 text-right">{pct}</span>
      </div>

      {narrative.price_current != null && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="font-mono">${narrative.price_current.toFixed(2)}</span>
          {narrative.price_change_7d_pct != null && (
            <span className={narrative.price_change_7d_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
              {formatPct(narrative.price_change_7d_pct)}
            </span>
          )}
        </div>
      )}

      <p className="text-xs text-gray-600 leading-relaxed line-clamp-3">{narrative.narrative}</p>

      {narrative.key_drivers.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-gray-100">
          {narrative.key_drivers.slice(0, 3).map((d, i) => (
            <span key={i} className="text-[10px] bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
              {d}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default CompanyCard
