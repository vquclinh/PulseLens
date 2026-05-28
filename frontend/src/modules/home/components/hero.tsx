import { useNavigate } from 'react-router-dom'
import type { PulseStatus, QualityStatus } from '@/types'

const PULSE_STATUS_LABELS: Record<PulseStatus, string> = {
  heating_up: 'Heating Up',
  stable: 'Stable',
  cooling_down: 'Cooling Down',
  volatile: 'Volatile',
  risk_rising: 'Risk Rising',
}

interface HeroProps {
  pulseScore: number
  pulseStatus: PulseStatus
  pulseConfidence: number
  qualityStatus?: QualityStatus
  evidenceCount: number
  sourceCount: number
  generatedAt: string
  isLive: boolean
}

export default function Hero({
  pulseScore,
  pulseStatus,
  pulseConfidence,
  qualityStatus,
  evidenceCount,
  sourceCount,
  generatedAt,
  isLive,
}: HeroProps) {
  const navigate = useNavigate()
  const statusLabel = PULSE_STATUS_LABELS[pulseStatus] ?? pulseStatus
  const qualityLabel = qualityStatus ?? (isLive ? 'Live report' : 'Demo baseline')

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-16">
      <div className="max-w-7xl mx-auto grid grid-cols-[1.3fr_0.7fr] gap-10 items-center">
        <div className="max-w-3xl flex flex-col gap-5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 uppercase tracking-wide">
              US AI Hardware · Live
            </span>
            {!isLive && (
              <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                Demo baseline
              </span>
            )}
          </div>
          <h1 className="text-5xl font-bold text-gray-950 leading-[1.05] tracking-normal">
            AI Hardware Market Intelligence
          </h1>
          <p className="text-xl text-gray-600 leading-relaxed max-w-2xl">
            Grounded signals, not AI summaries — every claim traces back to a source.{' '}
            {evidenceCount} evidence facts from {sourceCount} sources, triangulated and scored.
            {!isLive && ' Demo baseline shown until the backend is available.'}
          </p>
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => navigate('/workspace')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm"
            >
              Open Workspace →
            </button>
            <a
              href="#how-it-works"
              className="px-6 py-3 border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              How It Works ↓
            </a>
          </div>
        </div>

        <div className="bg-gray-950 text-white rounded-2xl p-6 shadow-xl border border-gray-800 flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-blue-200 uppercase tracking-wide">Market Read</span>
            <span className={isLive ? 'text-xs text-green-300' : 'text-xs text-amber-300'}>
              {isLive ? 'Live backend' : 'Fallback'}
            </span>
          </div>
          <div className="flex items-end gap-3">
            <span className="text-6xl font-bold tabular-nums leading-none">{pulseScore.toFixed(1)}</span>
            <span className="text-sm text-gray-400 mb-2">/ 100</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-white/5 border border-white/10 p-3">
              <div className="text-[11px] text-gray-400 uppercase tracking-wide">Pulse Status</div>
              <div className="text-base font-semibold mt-1">{statusLabel}</div>
            </div>
            <div className="rounded-lg bg-white/5 border border-white/10 p-3">
              <div className="text-[11px] text-gray-400 uppercase tracking-wide">Quality</div>
              <div className="text-base font-semibold mt-1">{qualityLabel}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-gray-400">Generated</div>
              <div className="font-medium">{generatedAt}</div>
            </div>
            <div>
              <div className="text-gray-400">Confidence</div>
              <div className="font-medium">{(pulseConfidence * 100).toFixed(0)}%</div>
            </div>
          </div>
          <div className="border-t border-white/10 pt-4 text-sm text-gray-300">
            {evidenceCount} evidence facts across {sourceCount} sources
          </div>
        </div>
      </div>
    </div>
  )
}
