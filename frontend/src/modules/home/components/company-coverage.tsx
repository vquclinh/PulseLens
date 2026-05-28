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
  evidenceCount?: number | null
}

interface CompanyCoverageProps {
  companies: CompanyCardData[]
  activeCompany: string
  onCompanyChange: (company: string) => void
  isFallback?: boolean
}

function CompanyCard({
  company,
  ticker,
  momentum,
  key_drivers,
  evidenceCount,
  active,
  onSelect,
}: CompanyCardData & { active: boolean; onSelect: () => void }) {
  const cfg = MOMENTUM_CFG[momentum] ?? MOMENTUM_CFG.neutral
  const navigate = useNavigate()

  return (
    <div className={[
      'bg-white border rounded-2xl p-5 flex flex-col gap-4 shadow-sm transition-colors',
      active ? 'border-blue-300 ring-2 ring-blue-100' : 'border-gray-200 hover:border-gray-300',
    ].join(' ')}>
      <div className="flex items-center justify-between">
        <div>
          <span className="text-lg font-bold text-gray-950">{company}</span>
          <span className="text-xs text-gray-400 ml-2 font-mono">{ticker}</span>
        </div>
        <span className={`text-xs font-semibold px-2 py-1 rounded border ${cfg.cls}`}>
          {cfg.label}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {key_drivers.slice(0, 3).map(d => (
          <span key={d} className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
            {d}
          </span>
        ))}
      </div>
      <div className="text-sm text-gray-500">
        {evidenceCount == null ? 'Evidence loading' : `${evidenceCount} evidence facts`}
      </div>
      <div className="flex items-center gap-3 mt-auto">
        <button
          onClick={onSelect}
          className="text-sm text-blue-600 hover:text-blue-700 font-semibold text-left"
        >
          Filter facts
        </button>
        <button
          onClick={() => navigate('/workspace/companies')}
          className="text-sm text-gray-500 hover:text-gray-800 font-medium text-left"
        >
          Open company view →
        </button>
      </div>
    </div>
  )
}

export default function CompanyCoverage({
  companies,
  activeCompany,
  onCompanyChange,
  isFallback = false,
}: CompanyCoverageProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-950">Company Coverage</h2>
          <p className="text-sm text-gray-500 mt-1">Filter evidence by tracked company.</p>
        </div>
        <span className={isFallback ? 'text-xs text-amber-600' : 'text-xs text-gray-400'}>
          {isFallback ? 'fallback narratives' : companies.map(c => c.ticker).join(' · ')}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onCompanyChange('all')}
          className={[
            'px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
            activeCompany === 'all'
              ? 'bg-gray-950 text-white border-gray-950'
              : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
          ].join(' ')}
        >
          All companies
        </button>
        {companies.map(c => (
          <button
            key={c.company}
            onClick={() => onCompanyChange(c.company)}
            className={[
              'px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
              activeCompany === c.company
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
            ].join(' ')}
          >
            {c.ticker}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        {companies.map(c => (
          <CompanyCard
            key={c.company}
            {...c}
            active={activeCompany === c.company}
            onSelect={() => onCompanyChange(c.company)}
          />
        ))}
      </div>
    </div>
  )
}
