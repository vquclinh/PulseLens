// Evidence filter controls — dropdowns for company, signal type, tier, sentiment, min confidence
import type { FC } from 'react'
import { cn } from '@/lib/utils'

interface EvidenceFiltersProps {
  filters: Record<string, string>
  onChange: (k: string, v: string) => void
}

const SIGNAL_OPTIONS = [
  { value: '', label: 'All Signals' },
  { value: 'hiring_momentum', label: 'Hiring Momentum' },
  { value: 'product_launch', label: 'Product Launch' },
  { value: 'pricing_pressure', label: 'Pricing Pressure' },
  { value: 'strategic_messaging', label: 'Strategic Messaging' },
  { value: 'investor_signal', label: 'Investor Signal' },
  { value: 'news_sentiment', label: 'News Sentiment' },
  { value: 'supplier_risk', label: 'Supplier Risk' },
]

const TIER_OPTIONS = [
  { value: '', label: 'All Tiers' },
  { value: '1', label: 'Tier 1' },
  { value: '2', label: 'Tier 2' },
  { value: '3', label: 'Tier 3' },
  { value: '4', label: 'Tier 4' },
]

const SENTIMENT_OPTIONS = [
  { value: '', label: 'All Sentiment' },
  { value: 'positive', label: 'Positive' },
  { value: 'negative', label: 'Negative' },
  { value: 'neutral', label: 'Neutral' },
]

const selectCls = cn(
  'text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700',
  'focus:outline-none focus:ring-2 focus:ring-blue-500',
)

const EvidenceFilters: FC<EvidenceFiltersProps> = ({ filters, onChange }) => {
  return (
    <div className="flex flex-wrap gap-2 items-center">
      <input
        type="text"
        placeholder="Search entity…"
        value={filters.entity ?? ''}
        onChange={(e) => onChange('entity', e.target.value)}
        className={cn(selectCls, 'w-40')}
      />

      <select
        value={filters.signal_type ?? ''}
        onChange={(e) => onChange('signal_type', e.target.value)}
        className={selectCls}
      >
        {SIGNAL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      <select
        value={filters.tier ?? ''}
        onChange={(e) => onChange('tier', e.target.value)}
        className={selectCls}
      >
        {TIER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      <select
        value={filters.sentiment ?? ''}
        onChange={(e) => onChange('sentiment', e.target.value)}
        className={selectCls}
      >
        {SENTIMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      <input
        type="number"
        placeholder="Min conf."
        min="0"
        max="1"
        step="0.1"
        value={filters.min_confidence ?? ''}
        onChange={(e) => onChange('min_confidence', e.target.value)}
        className={cn(selectCls, 'w-24')}
      />
    </div>
  )
}

export default EvidenceFilters
