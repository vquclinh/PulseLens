// Dashboard topbar — PulseLens brand, breadcrumb, pulse status badge, score, time window
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import { useDashboardStore } from '@/store/dashboard-store'
import { formatDate } from '@/lib/utils'

interface TopbarProps {
  report: MarketPulseReport | undefined
  onRefresh: () => void
  isRefreshing: boolean
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

const Topbar: FC<TopbarProps> = ({ report, onRefresh, isRefreshing }) => {
  const { isChatOpen, setIsChatOpen } = useDashboardStore()

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-900 tracking-tight">PulseLens</span>
          <span className="text-gray-300">›</span>
          <span className="text-sm text-gray-600">{report?.market ?? 'Loading…'}</span>
        </div>

        {report && (
          <>
            <div className="flex items-center gap-1.5 ml-2">
              <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[report.pulse_status] ?? 'bg-gray-400'}`} />
              <span className="text-xs font-medium text-gray-700">
                {STATUS_LABELS[report.pulse_status] ?? report.pulse_status}
              </span>
            </div>

            <span className="text-2xl font-bold text-gray-900 tabular-nums">
              {report.pulse_score.toFixed(1)}
            </span>

            <span className="text-xs text-gray-400 hidden sm:block">
              {report.time_window} · {formatDate(report.generated_at)}
            </span>
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {isRefreshing ? 'Running…' : 'Refresh'}
          </button>
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            className={`text-xs font-medium border rounded-lg px-3 py-1.5 transition-colors ${
              isChatOpen
                ? 'bg-blue-600 text-white border-blue-600'
                : 'text-blue-600 border-blue-300 hover:bg-blue-50'
            }`}
          >
            {isChatOpen ? 'Close Chat' : 'Ask AI'}
          </button>
        </div>
      </div>
    </header>
  )
}

export default Topbar
