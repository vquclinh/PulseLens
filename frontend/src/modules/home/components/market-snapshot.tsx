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
  avgFactConfidence: number | null
  safeVerifiedFactCount: number | null
  factsLoading: boolean
  factsUnavailable: boolean
  qualityStatus?: string
  isLive: boolean
  generatedAt: string
}

export default function MarketSnapshot({
  pulseScore,
  pulseStatus,
  pulseConfidence,
  evidenceCount,
  sourceCount,
  avgFactConfidence,
  safeVerifiedFactCount,
  factsLoading,
  factsUnavailable,
  qualityStatus,
  isLive,
  generatedAt,
}: MarketSnapshotProps) {
  const statusLabel = PULSE_STATUS_LABELS[pulseStatus] ?? pulseStatus
  const statusColor = PULSE_STATUS_COLORS[pulseStatus] ?? 'bg-gray-400'

  const evidenceSubStat = avgFactConfidence != null
    ? `Avg confidence ${(avgFactConfidence * 100).toFixed(0)}%${
        safeVerifiedFactCount != null ? ` · ${safeVerifiedFactCount} SAFE verified` : ''
      }`
    : isLive
    ? 'Fact confidence loads from live evidence'
    : 'Demo baseline'

  const qualityLabel = qualityStatus ?? (isLive ? 'PASS' : 'Demo baseline')
  const safeFactDisplay = factsLoading ? '...' : safeVerifiedFactCount ?? '—'
  const safeFactCopy = factsLoading
    ? 'Checking fact-level verification'
    : factsUnavailable
    ? 'Fact-level verification unavailable'
    : safeVerifiedFactCount == null
    ? 'Waiting for fact evidence'
    : 'evidence-anchored'
  const safeFactDetail = factsUnavailable
    ? 'Facts API unavailable'
    : 'Evidence quotes checked against source text'

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-950">Market Snapshot</h2>
          <p className="text-sm text-gray-500 mt-1">Live report health, evidence depth, and verification state.</p>
        </div>
        {isLive ? (
          <span className="text-xs text-green-600 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
            Live data
          </span>
        ) : (
          <span className="text-xs text-amber-600 font-medium">Demo baseline · {generatedAt}</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Pulse score card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-4 shadow-sm">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Pulse Score</span>
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
          <div className="text-sm text-gray-500 border-t border-gray-100 pt-3">
            Confidence {(pulseConfidence * 100).toFixed(0)}% · US AI Hardware
          </div>
        </div>

        {/* Evidence card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-4 shadow-sm">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Evidence / Sources</span>
          <div className="flex items-end gap-2">
            <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
              {evidenceCount}
            </span>
            <span className="text-sm text-gray-400 mb-1">facts</span>
          </div>
          <div className="text-base font-medium text-gray-700">
            from {sourceCount} unique sources
          </div>
          <div className="text-sm text-gray-500 border-t border-gray-100 pt-3">
            {evidenceSubStat}
          </div>
        </div>

        {/* SAFE verified facts card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-4 shadow-sm">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">SAFE-verified Facts</span>
          <div className="flex items-end gap-2">
            <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
              {safeFactDisplay}
            </span>
            <span className="text-sm text-gray-400 mb-1">facts</span>
          </div>
          <div className="text-base font-medium text-gray-700">
            {safeFactCopy}
          </div>
          <div className="text-sm text-gray-500 border-t border-gray-100 pt-3">
            {safeFactDetail} · Quality: {qualityLabel}
          </div>
        </div>
      </div>
      {!isLive && <div className="text-xs text-amber-600">Demo baseline — not investment advice</div>}
    </div>
  )
}
