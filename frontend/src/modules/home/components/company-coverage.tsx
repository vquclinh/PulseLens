import { useNavigate } from 'react-router-dom'
import type { MomentumLabel } from '@/types'

const MOMENTUM_CFG: Record<MomentumLabel, { label: string; cls: string }> = {
  strong_positive: { label: 'Strong ↑', cls: 'bg-green-100 text-green-800 border-green-200' },
  positive:        { label: 'Positive ↑', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  neutral:         { label: 'Neutral →', cls: 'bg-gray-100 text-gray-600 border-gray-200' },
  mixed:           { label: 'Mixed ↕', cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  negative:        { label: 'Negative ↓', cls: 'bg-red-50 text-red-700 border-red-200' },
  elevated_risk:   { label: 'Risk ⚠', cls: 'bg-purple-100 text-purple-800 border-purple-200' },
}

interface CompanyCardData {
  company: string
  ticker: string
  momentum: MomentumLabel
  key_drivers: string[]
}

interface CompanyCoverageProps {
  companies: CompanyCardData[]
}

function CompanyCard({ company, ticker, momentum, key_drivers }: CompanyCardData) {
  const cfg = MOMENTUM_CFG[momentum] ?? MOMENTUM_CFG.neutral
  const navigate = useNavigate()

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-bold text-gray-900">{company}</span>
          <span className="text-xs text-gray-400 ml-2 font-mono">{ticker}</span>
        </div>
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${cfg.cls}`}>
          {cfg.label}
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {key_drivers.slice(0, 3).map(d => (
          <span key={d} className="text-[10px] text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">
            {d}
          </span>
        ))}
      </div>
      <button
        onClick={() => navigate('/dashboard/us-ai-hardware')}
        className="text-xs text-blue-600 hover:text-blue-700 font-medium text-left mt-auto"
      >
        View in Dashboard →
      </button>
    </div>
  )
}

export default function CompanyCoverage({ companies }: CompanyCoverageProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Company Coverage</h2>
        <span className="text-xs text-gray-400">AMD · Nvidia · Supermicro</span>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {companies.map(c => (
          <CompanyCard key={c.company} {...c} />
        ))}
      </div>
    </div>
  )
}
