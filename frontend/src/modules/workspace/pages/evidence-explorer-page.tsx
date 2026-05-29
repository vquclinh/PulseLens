import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { FactObject, MarketPulseReport, SignalType } from '@/types/api'
import { formatDate } from '@/lib/utils'
import SentimentBadge from '@/shared/components/sentiment-badge'
import TierBadge from '@/shared/components/tier-badge'
import { Check, Copy, ExternalLink, MessageSquare } from 'lucide-react'

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

const VALID_SIGNALS: ReadonlySet<string> = new Set(
  SIGNAL_OPTIONS.filter(o => o.value !== 'all').map(o => o.value),
)

const ENTITY_BASE_OPTIONS = ['Nvidia', 'AMD', 'Supermicro', 'market']

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

function normalizedText(fact: FactObject): string {
  return [fact.claim, fact.evidence_quote, fact.entity, fact.source_url, sourceDomain(fact.source_url), fact.signal_type]
    .join(' ').toLowerCase()
}

function publishedTime(fact: FactObject): number {
  if (!fact.published_date) return 0
  const parsed = Date.parse(fact.published_date)
  return Number.isFinite(parsed) ? parsed : 0
}

function sortFacts(facts: FactObject[], sortMode: SortMode): FactObject[] {
  return [...facts].sort((a, b) => {
    if (sortMode === 'tier_asc') return a.source_tier - b.source_tier || b.confidence - a.confidence
    if (sortMode === 'newest') return publishedTime(b) - publishedTime(a) || b.confidence - a.confidence
    if (sortMode === 'signal_type') return a.signal_type.localeCompare(b.signal_type) || b.confidence - a.confidence
    return b.confidence - a.confidence
  })
}

// ─── Summary chips ────────────────────────────────────────────────────────────

function SummaryChips({ total, safeCount, domainCount, tier12Count }: {
  total: number; safeCount: number; domainCount: number; tier12Count: number
}) {
  return (
    <div className="flex flex-wrap gap-3">
      {[
        { label: 'Total facts', value: total },
        { label: 'SAFE-verified', value: safeCount },
        { label: 'Source domains', value: domainCount },
        { label: 'Tier 1/2 sources', value: tier12Count },
      ].map(({ label, value }) => (
        <div key={label} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 shadow-sm">
          <span className="text-xl font-bold text-gray-900 tabular-nums">{value}</span>
          <span className="text-xs text-gray-500">{label}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Filter select control ────────────────────────────────────────────────────

function SelectControl({ label, value, onChange, children }: {
  label: string; value: string; onChange: (value: string) => void; children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {children}
      </select>
    </label>
  )
}

// ─── Evidence card — richer 2-column grid card ────────────────────────────────
//
// Default: claim clamped 2 lines, quote clamped 2 lines — enough to understand
//          the evidence at a glance.
// Selected (expanded): full unclamped claim + quote, blue ring.
//
// The grid uses default stretch (no items-start) for equal-height rows.
// h-full + flex-col + mt-auto footer ensures both cards in a row stay the
// same height and action buttons align at the bottom.
// When a selected card expands, only its grid row grows; all other rows
// are unaffected.

function EvidenceCard({ fact, isSelected, onClick }: {
  fact: FactObject; isSelected: boolean; onClick: () => void
}) {
  const [copied, setCopied] = useState(false)
  const domain = sourceDomain(fact.source_url)

  function handleCopy(e: React.MouseEvent) {
    e.stopPropagation()
    void navigator.clipboard?.writeText(fact.evidence_quote)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <article
      className={[
        'rounded-2xl border bg-white p-5 shadow-sm flex flex-col gap-3 transition-shadow h-full',
        isSelected
          ? 'border-blue-400 ring-2 ring-blue-100 ring-offset-1 shadow-md'
          : 'border-gray-200 hover:border-blue-200 hover:shadow',
      ].join(' ')}
    >
      {/* ── Top row: badges ── */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 whitespace-nowrap">
          {fact.signal_type.replace(/_/g, ' ')}
        </span>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-700 whitespace-nowrap">
          {fact.entity}
        </span>
        {fact.safe_verified && (
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
            SAFE
          </span>
        )}
        <div className="ml-auto flex items-center gap-1.5 shrink-0">
          <TierBadge tier={fact.source_tier} />
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>

      {/* ── Claim — clickable to expand/collapse ── */}
      <h3
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
        aria-expanded={isSelected}
        className={[
          'cursor-pointer text-sm font-bold leading-snug text-gray-950',
          isSelected ? '' : 'line-clamp-2',
        ].join(' ')}
      >
        {fact.claim}
      </h3>

      {/* ── Evidence quote ── */}
      <blockquote
        className={[
          'border-l-4 border-blue-200 pl-3 text-xs italic leading-5 text-gray-600',
          isSelected ? '' : 'line-clamp-2',
        ].join(' ')}
      >
        "{fact.evidence_quote}"
      </blockquote>

      {/* ── Meta: source · confidence · date ── */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-gray-500">
        <span className="font-semibold text-gray-700">{domain}</span>
        <span>·</span>
        <span>{(fact.confidence * 100).toFixed(0)}% conf</span>
        {fact.published_date && (
          <>
            <span>·</span>
            <span>{formatDate(fact.published_date)}</span>
          </>
        )}
      </div>
      {/* fact_id kept internally for Ask Chat / context links — not shown in card UI */}

      {/* ── Footer actions ── */}
      <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-2.5 mt-auto">
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
        <a
          href={fact.source_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Source
        </a>
        <Link
          to={`/chat?context=fact&fact_id=${fact.fact_id}`}
          className="ml-auto flex items-center gap-1.5 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Ask Chat
        </Link>
      </div>
    </article>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function EvidenceExplorerPage({
  report,
  facts,
  factsLoading,
  factsError,
}: EvidenceExplorerPageProps) {
  const [searchParams, setSearchParams] = useSearchParams()

  const signalParam = searchParams.get('signal')
  const initialLinkedSignal: SignalType | null =
    signalParam && VALID_SIGNALS.has(signalParam) ? (signalParam as SignalType) : null

  const [search, setSearch] = useState('')
  const [signalFilter, setSignalFilter] = useState<SignalType | 'all'>(initialLinkedSignal ?? 'all')
  const [linkedSignal, setLinkedSignal] = useState<SignalType | null>(initialLinkedSignal)
  const [entityFilter, setEntityFilter] = useState('all')
  const [tierFilter, setTierFilter] = useState<TierFilter>('all')
  const [safeFilter, setSafeFilter] = useState<SafeFilter>('all')
  const [sortMode, setSortMode] = useState<SortMode>('confidence_desc')
  const [selectedFact, setSelectedFact] = useState<FactObject | null>(null)

  const filterAreaRef = useRef<HTMLDivElement>(null)
  const NAVBAR_H = 72

  useEffect(() => {
    if (initialLinkedSignal && filterAreaRef.current) {
      const top =
        filterAreaRef.current.getBoundingClientRect().top +
        window.scrollY - NAVBAR_H - 8
      window.scrollTo({ top: Math.max(0, top) })
    } else {
      window.scrollTo(0, 0)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const sourceDomains = useMemo(() => new Set(facts.map(f => sourceDomain(f.source_url))), [facts])
  const tierOneTwoDomains = useMemo(
    () => new Set(facts.filter(f => f.source_tier <= 2).map(f => sourceDomain(f.source_url))),
    [facts],
  )
  const safeVerifiedCount = facts.filter(f => f.safe_verified).length

  const entityOptions = useMemo(() => {
    const live = Array.from(new Set(facts.map(f => f.entity).filter(Boolean)))
    return Array.from(new Set(['all', ...ENTITY_BASE_OPTIONS, ...live]))
  }, [facts])

  const filteredFacts = useMemo(() => {
    const q = search.trim().toLowerCase()
    return sortFacts(
      facts.filter(fact => {
        if (q && !normalizedText(fact).includes(q)) return false
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
    if (linkedSignal) {
      setLinkedSignal(null)
      setSearchParams(p => { p.delete('signal'); return p })
    }
  }

  function clearLinkedFilter() {
    setSignalFilter('all')
    setLinkedSignal(null)
    setSearchParams(p => { p.delete('signal'); return p })
  }

  function handleCardClick(fact: FactObject) {
    setSelectedFact(prev => prev?.fact_id === fact.fact_id ? null : fact)
  }

  const linkedSignalLabel = linkedSignal
    ? (SIGNAL_OPTIONS.find(o => o.value === linkedSignal)?.label ?? linkedSignal)
    : null

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
    <section className="flex flex-col gap-5">
      {/* Page header */}
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-5 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Evidence Explorer</p>
            <h2 className="mt-1 text-2xl font-bold text-gray-950">Source-backed facts</h2>
            <p className="mt-1 text-sm text-gray-500">
              {facts.length} facts · <span className="font-mono text-xs">{report.report_id}</span>
            </p>
          </div>
          <SummaryChips
            total={facts.length}
            safeCount={safeVerifiedCount}
            domainCount={sourceDomains.size}
            tier12Count={tierOneTwoDomains.size}
          />
        </div>
      </div>

      {/* Scroll anchor for deep-link from Signal Cockpit */}
      <div ref={filterAreaRef} />

      {/* Linked filter banner */}
      {linkedSignal && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-blue-200 bg-blue-50/60 px-5 py-3">
          <p className="text-sm text-blue-800">
            Showing evidence linked from Signal Cockpit:{' '}
            <span className="font-semibold">{linkedSignalLabel}</span>
          </p>
          <button
            type="button"
            onClick={clearLinkedFilter}
            className="shrink-0 rounded-lg border border-blue-300 bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50"
          >
            Clear linked filter
          </button>
        </div>
      )}

      {/* Filter controls */}
      <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_1fr_1fr]">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">Search</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Claim, quote, entity, domain…"
              className="h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </label>

          <SelectControl label="Signal" value={signalFilter} onChange={v => setSignalFilter(v as SignalType | 'all')}>
            {SIGNAL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </SelectControl>

          <SelectControl label="Entity" value={entityFilter} onChange={setEntityFilter}>
            {entityOptions.map(e => <option key={e} value={e}>{e === 'all' ? 'All Entities' : e}</option>)}
          </SelectControl>

          <SelectControl label="Tier" value={tierFilter} onChange={v => setTierFilter(v as TierFilter)}>
            <option value="all">All Tiers</option>
            <option value="1">Tier 1</option>
            <option value="2">Tier 2</option>
            <option value="3">Tier 3</option>
            <option value="4">Tier 4</option>
          </SelectControl>

          <SelectControl label="SAFE" value={safeFilter} onChange={v => setSafeFilter(v as SafeFilter)}>
            <option value="all">All Facts</option>
            <option value="safe_only">SAFE only</option>
          </SelectControl>
        </div>

        <div className="mt-3 flex flex-wrap items-end justify-between gap-3 border-t border-gray-100 pt-3">
          <SelectControl label="Sort" value={sortMode} onChange={v => setSortMode(v as SortMode)}>
            <option value="confidence_desc">Confidence ↓</option>
            <option value="tier_asc">Source tier ↑</option>
            <option value="newest">Newest date</option>
            <option value="signal_type">Signal type</option>
          </SelectControl>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{filteredFacts.length} matching facts</span>
            <button
              type="button"
              onClick={clearFilters}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Clear filters
            </button>
          </div>
        </div>
      </div>

      {/* Empty states */}
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
          <p className="mt-2 text-sm text-gray-500">
            {linkedSignal
              ? `No evidence facts for ${linkedSignalLabel} in the latest report.`
              : 'Clear filters or broaden the search query.'}
          </p>
        </div>
      ) : (
        /*
         * Equal-height 2-column grid — no items-start, default stretch.
         * h-full on each article + flex-col + mt-auto footer = consistent height rows.
         * When a card expands (selected), only its grid row grows; other rows
         * are unaffected.
         */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFacts.map(fact => (
            <EvidenceCard
              key={fact.fact_id}
              fact={fact}
              isSelected={selectedFact?.fact_id === fact.fact_id}
              onClick={() => handleCardClick(fact)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
