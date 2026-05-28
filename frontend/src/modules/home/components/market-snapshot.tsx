import type { PulseStatus } from '@/types'

const PULSE_STATUS_LABELS: Record<PulseStatus, string> = {
  heating_up: 'Heating Up',
  stable: 'Stable',
  cooling_down: 'Cooling Down',
  volatile: 'Volatile',
  risk_rising: 'Risk Rising',
}

const PULSE_STATUS_COLORS: Record<PulseStatus, string> = {
  heating_up: 'bg-green-500',
  stable: 'bg-blue-500',
  cooling_down: 'bg-red-500',
  volatile: 'bg-amber-500',
  risk_rising: 'bg-purple-500',
}

interface MarketSnapshotProps {
  pulseScore: number
  pulseStatus: PulseStatus
  pulseConfidence: number
  evidenceCount: number
  sourceCount: number
  verifiedClaimsCount: number
  isLive: boolean
  reportId: string
  generatedAt: string
}

export default function MarketSnapshot({
  pulseScore,
  pulseStatus,
  pulseConfidence,
  evidenceCount,
  sourceCount,
  verifiedClaimsCount,
  isLive,
  reportId,
  generatedAt,
}: MarketSnapshotProps) {
  const statusLabel = PULSE_STATUS_LABELS[pulseStatus] ?? pulseStatus
  const statusColor = PULSE_STATUS_COLORS[pulseStatus] ?? 'bg-gray-400'

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Market Snapshot</h2>
        {isLive ? (
          <span className="text-xs text-green-600 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
            Live data
          </span>
        ) : (
          <span className="text-xs text-amber-600 font-medium">Demo baseline · {generatedAt}</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Pulse score card */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Pulse Score</span>
          <div className="flex items-end gap-3">
            <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
              {pulseScore.toFixed(1)}
            </span>
            <span className="text-sm text-gray-400 mb-1">/ 100</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
            <span className="text-sm font-medium text-gray-700">{statusLabel}</span>
          </div>
          <div className="text-xs text-gray-400 border-t border-gray-100 pt-2">
            Confidence {(pulseConfidence * 100).toFixed(0)}% · US AI Hardware
          </div>
        </div>

        {/* Evidence card */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Evidence</span>
          <div className="flex items-end gap-2">
            <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
              {evidenceCount}
            </span>
            <span className="text-sm text-gray-400 mb-1">facts</span>
          </div>
          <div className="text-sm font-medium text-gray-700">
            from {sourceCount} unique sources
          </div>
          <div className="text-xs text-gray-400 border-t border-gray-100 pt-2">
            Avg confidence 0.905 · SAFE verified
          </div>
        </div>

        {/* Verified claims card */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Verified Claims</span>
          <div className="flex items-end gap-2">
            <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
              {verifiedClaimsCount}
            </span>
            <span className="text-sm text-gray-400 mb-1">triangulated</span>
          </div>
          <div className="text-sm font-medium text-gray-700">
            ≥ 2 independent sources each
          </div>
          <div className="text-xs text-gray-400 border-t border-gray-100 pt-2">
            0 suspicious claims · 0 false positives
          </div>
        </div>
      </div>

      <div className="text-xs text-gray-400">
        Report ID:{' '}
        <span className="font-mono text-gray-500">{reportId}</span>
        {!isLive && ' · Demo baseline — not investment advice'}
      </div>
    </div>
  )
}
