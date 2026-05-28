import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { FactObject, MarketPulseReport, SignalType } from '@/types/api'
import { formatDate } from '@/lib/utils'
import SentimentBadge from '@/shared/components/sentiment-badge'
import TierBadge from '@/shared/components/tier-badge'

interface EvidenceExplorerPageProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
  factsError: Error | null
}

type SortMode = 'confidence_desc' | 'tier_asc' | 'newest' | 'signal_type'
type SafeFilter = 'all' | 'safe_only'
type TierFilter = 'all' | '1' | '2' | '3' | '4'

const SIGNAL_OPTIONS: { value: SignalType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Signals' },
  { value: 'pricing_pressure', label: 'Pricing Pressure' },
  { value: 'product_launch', label: 'Product Launch' },
  { value: 'investor_signal', label: 'Investor Signal' },
  { value: 'strategic_messaging', label: 'Strategic Messaging' },
  { value: 'supplier_risk', label: 'Supplier Risk' },
  { value: 'news_sentiment', label: 'News Sentiment' },
  { value: 'hiring_momentum', label: 'Hiring Momentum' },
]

const ENTITY_BASE_OPTIONS = ['Nvidia', 'AMD', 'Supermicro', 'market']

function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function normalizedText(fact: FactObject): string {
  return [
    fact.claim,
    fact.evidence_quote,
    fact.entity,
    fact.source_url,
    sourceDomain(fact.source_url),
    fact.signal_type,
  ].join(' ').toLowerCase()
}

function publishedTime(fact: FactObject): number {
  if (!fact.published_date) return 0
  const parsed = Date.parse(fact.published_date)
  return Number.isFinite(parsed) ? parsed : 0
}

function sortFacts(facts: FactObject[], sortMode: SortMode): FactObject[] {
  return [...facts].sort((a, b) => {
    if (sortMode === 'tier_asc') {
      return a.source_tier - b.source_tier || b.confidence - a.confidence
    }
    if (sortMode === 'newest') {
      return publishedTime(b) - publishedTime(a) || b.confidence - a.confidence
    }
    if (sortMode === 'signal_type') {
      return a.signal_type.localeCompare(b.signal_type) || b.confidence - a.confidence
    }
    return b.confidence - a.confidence
  })
}

function SummaryCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-gray-950">{value}</p>
      <p className="mt-2 text-sm text-gray-500">{detail}</p>
    </div>
  )
}

function SelectControl({
  label,
  value,
  onChange,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {children}
      </select>
    </label>
  )
}

function EvidenceCard({ fact }: { fact: FactObject }) {
  const domain = sourceDomain(fact.source_url)

  function copyQuote() {
    void navigator.clipboard?.writeText(fact.evidence_quote)
  }

  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
          {fact.signal_type.replace(/_/g, ' ')}
        </span>
        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
          {fact.entity}
        </span>
        {fact.safe_verified && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            SAFE verified
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <TierBadge tier={fact.source_tier} />
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>

      <h3 className="mt-4 text-lg font-bold leading-snug text-gray-950">{fact.claim}</h3>
      <blockquote className="mt-4 border-l-4 border-blue-200 pl-4 text-base leading-7 text-gray-700">
        "{fact.evidence_quote}"
      </blockquote>

      <div className="mt-5 grid gap-3 text-sm text-gray-500 md:grid-cols-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Source</p>
          <p className="mt-1 font-semibold text-gray-800">{domain}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Confidence</p>
          <p className="mt-1 font-semibold text-gray-800">{(fact.confidence * 100).toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Published</p>
          <p className="mt-1 font-semibold text-gray-800">{formatDate(fact.published_date) || 'Unavailable'}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Fact ID</p>
          <p className="mt-1 truncate font-mono text-xs text-gray-500">{fact.fact_id}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-gray-100 pt-4">
        <button
          type="button"
          onClick={copyQuote}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        >
          Copy quote
        </button>
        <a
          href={fact.source_url}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        >
          Open source
        </a>
        <Link
          to="/chat"
          className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Ask Chat
        </Link>
      </div>
    </article>
  )
}

export default function EvidenceExplorerPage({
  report,
  facts,
  factsLoading,
  factsError,
}: EvidenceExplorerPageProps) {
  const [search, setSearch] = useState('')
  const [signalFilter, setSignalFilter] = useState<SignalType | 'all'>('all')
  const [entityFilter, setEntityFilter] = useState('all')
  const [tierFilter, setTierFilter] = useState<TierFilter>('all')
  const [safeFilter, setSafeFilter] = useState<SafeFilter>('all')
  const [sortMode, setSortMode] = useState<SortMode>('confidence_desc')

  const sourceDomains = useMemo(() => new Set(facts.map((fact) => sourceDomain(fact.source_url))), [facts])
  const tierOneTwoDomains = useMemo(
    () => new Set(facts.filter((fact) => fact.source_tier <= 2).map((fact) => sourceDomain(fact.source_url))),
    [facts],
  )
  const safeVerifiedCount = facts.filter((fact) => fact.safe_verified).length

  const entityOptions = useMemo(() => {
    const liveEntities = Array.from(new Set(facts.map((fact) => fact.entity).filter(Boolean)))
    return Array.from(new Set(['all', ...ENTITY_BASE_OPTIONS, ...liveEntities]))
  }, [facts])

  const filteredFacts = useMemo(() => {
    const searchText = search.trim().toLowerCase()
    return sortFacts(
      facts.filter((fact) => {
        if (searchText && !normalizedText(fact).includes(searchText)) return false
        if (signalFilter !== 'all' && fact.signal_type !== signalFilter) return false
        if (entityFilter !== 'all' && fact.entity.toLowerCase() !== entityFilter.toLowerCase()) return false
        if (tierFilter !== 'all' && fact.source_tier !== Number(tierFilter)) return false
        if (safeFilter === 'safe_only' && !fact.safe_verified) return false
        return true
      }),
      sortMode,
    )
  }, [entityFilter, facts, safeFilter, search, signalFilter, sortMode, tierFilter])

  function clearFilters() {
    setSearch('')
    setSignalFilter('all')
    setEntityFilter('all')
    setTierFilter('all')
    setSafeFilter('all')
    setSortMode('confidence_desc')
  }

  if (factsLoading) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-gray-400 animate-pulse">Loading latest evidence from the FastAPI backend...</p>
      </section>
    )
  }

  if (factsError) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Facts endpoint failed</p>
        <h2 className="mt-2 text-xl font-bold text-red-950">Unable to load evidence</h2>
        <p className="mt-2 text-sm text-red-700">{factsError.message}</p>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Evidence Explorer</p>
            <h2 className="mt-2 text-3xl font-bold text-gray-950">Source-backed facts from the latest report</h2>
            <p className="mt-3 max-w-3xl text-base leading-7 text-gray-600">
              Every card below is loaded from <span className="font-mono">/api/report/{report.report_id}/facts</span>.
              Use filters to inspect source quality, signal coverage, and the exact quoted evidence behind the report.
            </p>
          </div>
          <div className="text-sm text-gray-500">
            Report <span className="font-mono">{report.report_id}</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Total Facts" value={facts.length} detail="Loaded from facts endpoint" />
        <SummaryCard label="SAFE-verified" value={safeVerifiedCount} detail="Evidence quote checked" />
        <SummaryCard label="Source Domains" value={sourceDomains.size} detail="Unique domains represented" />
        <SummaryCard label="Tier 1/2 Sources" value={tierOneTwoDomains.size} detail="High-credibility domains" />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr]">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">Search</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Claim, quote, entity, domain, signal..."
              className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </label>

          <SelectControl label="Signal" value={signalFilter} onChange={(value) => setSignalFilter(value as SignalType | 'all')}>
            {SIGNAL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectControl>

          <SelectControl label="Entity" value={entityFilter} onChange={setEntityFilter}>
            {entityOptions.map((entity) => (
              <option key={entity} value={entity}>
                {entity === 'all' ? 'All Entities' : entity}
              </option>
            ))}
          </SelectControl>

          <SelectControl label="Tier" value={tierFilter} onChange={(value) => setTierFilter(value as TierFilter)}>
            <option value="all">All Tiers</option>
            <option value="1">Tier 1</option>
            <option value="2">Tier 2</option>
            <option value="3">Tier 3</option>
            <option value="4">Tier 4</option>
          </SelectControl>

          <SelectControl label="SAFE" value={safeFilter} onChange={(value) => setSafeFilter(value as SafeFilter)}>
            <option value="all">All Facts</option>
            <option value="safe_only">SAFE only</option>
          </SelectControl>
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-end sm:justify-between">
          <SelectControl label="Sort" value={sortMode} onChange={(value) => setSortMode(value as SortMode)}>
            <option value="confidence_desc">Confidence descending</option>
            <option value="tier_asc">Source tier ascending</option>
            <option value="newest">Newest published date</option>
            <option value="signal_type">Signal type</option>
          </SelectControl>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{filteredFacts.length} matching facts</span>
            <button
              type="button"
              onClick={clearFilters}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Clear filters
            </button>
          </div>
        </div>
      </div>

      {facts.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h3 className="text-xl font-bold text-gray-950">No evidence facts found</h3>
          <p className="mt-2 text-sm text-gray-500">
            The latest report loaded successfully, but the facts endpoint returned an empty list.
          </p>
        </div>
      ) : filteredFacts.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h3 className="text-xl font-bold text-gray-950">No facts match these filters</h3>
          <p className="mt-2 text-sm text-gray-500">Clear filters or broaden the search query.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredFacts.map((fact) => (
            <EvidenceCard key={fact.fact_id} fact={fact} />
          ))}
        </div>
      )}
    </section>
  )
}
