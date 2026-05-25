// Pulse score card — large score number, status badge, trend delta, 7-day sparkline
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import Sparkline from '@/shared/components/sparkline'
import { formatDate } from '@/lib/utils'

interface PulseScoreCardProps {
  report: MarketPulseReport
}

const STATUS_COLORS: Record<string, string> = {
  heating_up: 'bg-green-500',
  stable: 'bg-blue-500',
  cooling_down: 'bg-red-400',
  volatile: 'bg-amber-500',
  risk_rising: 'bg-purple-500',
}

const STATUS_LABELS: Record<string, string> = {
  heating_up: 'Heating Up',
  stable: 'Stable',
  cooling_down: 'Cooling Down',
  volatile: 'Volatile',
  risk_rising: 'Risk Rising',
}

const PulseScoreCard: FC<PulseScoreCardProps> = ({ report }) => {
  const statusColor = STATUS_COLORS[report.pulse_status] ?? 'bg-gray-500'
  const statusLabel = STATUS_LABELS[report.pulse_status] ?? report.pulse_status
  const sparkData = [
    report.pulse_score - (report.trend_vs_previous ?? 0),
    report.pulse_score,
  ]

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Pulse Score</span>
        <span className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
          <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
          {statusLabel}
        </span>
      </div>

      <div className="flex items-end gap-3">
        <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
          {report.pulse_score.toFixed(1)}
        </span>
        <span className="text-sm text-gray-400 mb-1">/ 100</span>
      </div>

      <div className="flex items-center gap-2">
        {report.trend_vs_previous !== null && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              report.trend_vs_previous >= 0
                ? 'text-green-600 bg-green-50'
                : 'text-red-600 bg-red-50'
            }`}
          >
            {report.trend_vs_previous >= 0 ? '+' : ''}
            {report.trend_vs_previous.toFixed(1)} vs last week
          </span>
        )}
        <span className="text-xs text-gray-400">
          Confidence {(report.pulse_confidence * 100).toFixed(0)}%
        </span>
      </div>

      {report.quality_status === 'PARTIAL_PASS' && (
        <div className="text-xs leading-relaxed text-amber-700 bg-amber-50 border border-amber-100 rounded-md px-3 py-2">
          Partial coverage: usable but incomplete. {report.quality_reasons.slice(0, 2).join('; ')}
        </div>
      )}

      <Sparkline data={sparkData} />

      <div className="text-xs text-gray-400 pt-1 border-t border-gray-100">
        {formatDate(report.generated_at)} · {report.evidence_count} facts · {report.source_count} sources
      </div>
    </div>
  )
}

export default PulseScoreCard
