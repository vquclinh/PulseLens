import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { FactObject, MarketPulseReport } from '@/types/api'
import { formatDate } from '@/lib/utils'
import SentimentBadge from '@/shared/components/sentiment-badge'
import TierBadge from '@/shared/components/tier-badge'
import {
  Search,
  Building2,
  ShieldCheck,
  TrendingDown,
  Calendar,
  ArrowUpDown,
  DollarSign,
  Copy,
  Check,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Layers,
  Globe,
  AlertTriangle,
  ArrowRight
} from 'lucide-react'

interface PricingPageProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
  factsError: Error | null
}

type SortMode = 'confidence_desc' | 'tier_asc' | 'newest' | 'source_domain'
type SafeFilter = 'all' | 'safe_only'
type TierFilter = 'all' | '1' | '2' | '3' | '4'

const GPU_MODELS = ['H100', 'H200', 'B200', 'Blackwell', 'MI300X', 'MI325X', 'MI355X', 'L40S', 'A100']

// Matches dollar pricing formats ($30,000, $3.50/hr, $20k, $1.5 million) exactly as they appear in the text
const PRICE_REGEX = /\$\d+(?:,\d{3})*(?:\.\d+)?\s*(?:k|K|m|M|billion|million|bn|b)?(?:\s*(?:-|to)\s*\$?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:k|K|m|M|billion|million|bn|b)?)?(?:\s*\/\s*(?:hr|hour|GPU\s*hr|A100\s*hr|H100\s*hr|GPU)|per\s*hour|per\s*GPU\s*hour)?/gi

function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function detectGPUs(claim: string, quote: string): string[] {
  const combined = `${claim} ${quote}`
  return GPU_MODELS.filter(model => {
    const regex = new RegExp(`\\b${model}(?:s)?\\b`, 'i')
    return regex.test(combined)
  })
}

function extractPriceSnippets(claim: string, quote: string): string[] {
  const combined = `${claim} ${quote}`
  const matches = combined.match(PRICE_REGEX)
  if (!matches) return []
  return Array.from(new Set(matches.map(m => m.trim())))
    .filter(Boolean)
    // Exclude zero-dollar junk ($0, $0.00) — these are scraper CSS/JS artifacts, not real prices
    .filter(snippet => !/^\$0(?:\.0+)?\s*$/.test(snippet))
}

// Display-only quote cleanup — strips common web scraper artifacts from rendered text.
// Does NOT mutate fact objects. The raw fact.evidence_quote is preserved for copy/search.
function displayQuote(raw: string): string {
  return raw
    // Remove <script ...>...</script> blocks
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    // Remove <style ...>...</style> blocks
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    // Remove any remaining HTML tags
    .replace(/<[^>]+>/g, '')
    // Remove CSS class/id fragments like .table-v2, #some-id
    .replace(/[.#][a-z][-\w]*(\s*\{[^}]*\})?/gi, '')
    // Remove JS patterns: function(), var x =, document., window.
    .replace(/\b(?:function\s*\(|var\s+\w|const\s+\w|let\s+\w|document\.|window\.|DOMScript)\S*/g, '')
    // Collapse excess whitespace
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function normalizedText(fact: FactObject): string {
  return [
    fact.claim,
    fact.evidence_quote,
    fact.entity,
    fact.source_url,
    sourceDomain(fact.source_url),
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
    if (sortMode === 'source_domain') {
      return sourceDomain(a.source_url).localeCompare(sourceDomain(b.source_url)) || b.confidence - a.confidence
    }
    return b.confidence - a.confidence
  })
}

// Single Evidence Card component to manage its copy quote state locally
function PricingFactCard({ fact }: { fact: FactObject }) {
  const [copied, setCopied] = useState(false)
  const domain = sourceDomain(fact.source_url)
  const detectedGPUs = useMemo(() => detectGPUs(fact.claim, fact.evidence_quote), [fact])
  const priceSnippets = useMemo(() => extractPriceSnippets(fact.claim, fact.evidence_quote), [fact])

  function copyQuote() {
    void navigator.clipboard?.writeText(fact.evidence_quote)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <article className="group relative rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:border-blue-200 hover:shadow-md transition-all duration-300">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
          {fact.entity}
        </span>
        {fact.safe_verified && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 flex items-center gap-1">
            <ShieldCheck className="h-3 w-3" />
            SAFE verified
          </span>
        )}
        <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
          {(fact.confidence * 100).toFixed(0)}% confidence
        </span>
        <div className="ml-auto flex items-center gap-2">
          <TierBadge tier={fact.source_tier} />
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>

      <h3 className="mt-4 text-lg font-bold leading-snug text-gray-950 group-hover:text-blue-900 transition-colors duration-200">
        {fact.claim}
      </h3>

      <blockquote className="mt-4 border-l-4 border-blue-200 pl-4 bg-slate-50/50 py-3 pr-3 rounded-r-xl text-base leading-relaxed text-gray-700 italic">
        "{displayQuote(fact.evidence_quote)}"
      </blockquote>

      {/* Extracted Non-Canonical Metadata */}
      {(detectedGPUs.length > 0 || priceSnippets.length > 0) && (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/40 p-3 text-xs">
          <span className="font-semibold text-slate-500 uppercase tracking-wide text-[10px] mr-1">
            Detected in evidence:
          </span>
          {detectedGPUs.map(gpu => (
            <span key={gpu} className="rounded-lg bg-blue-50/60 border border-blue-100 px-2 py-0.5 font-mono text-blue-700">
              {gpu}
            </span>
          ))}
          {priceSnippets.map(price => (
            <span key={price} className="rounded-lg bg-emerald-50/60 border border-emerald-100 px-2 py-0.5 font-mono text-emerald-700 flex items-center gap-0.5">
              <DollarSign className="h-3 w-3 shrink-0" />
              {price}
            </span>
          ))}
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4 text-sm">
        <div className="flex items-center gap-2 text-gray-500">
          <Globe className="h-4 w-4" />
          <span className="font-semibold text-gray-800">{domain}</span>
          <span className="text-gray-300">·</span>
          <span>{formatDate(fact.published_date) || 'Date unavailable'}</span>
        </div>
        <span className="font-mono text-[10px] text-gray-400">Fact ID: {fact.fact_id.substring(0, 12)}</span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-50 pt-3">
        <button
          type="button"
          onClick={copyQuote}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied!' : 'Copy quote'}
        </button>
        <a
          href={fact.source_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open source
        </a>
        <Link
          to="/chat?context=pricing"
          className="ml-auto flex items-center gap-1 rounded-lg bg-blue-600 hover:bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white transition-colors"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Ask Chat
        </Link>
      </div>
    </article>
  )
}

function PricingSkeleton() {
  return (
    <div className="grid gap-4 animate-pulse">
      {[1, 2, 3].map(i => (
        <div key={i} className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex gap-2">
            <div className="h-6 w-20 rounded bg-gray-200" />
            <div className="h-6 w-24 rounded bg-gray-200" />
            <div className="ml-auto h-6 w-16 rounded bg-gray-200" />
          </div>
          <div className="mt-4 h-6 w-3/4 rounded bg-gray-200" />
          <div className="mt-3 h-16 w-full rounded bg-gray-100" />
          <div className="mt-4 flex justify-between">
            <div className="h-4 w-32 rounded bg-gray-200" />
            <div className="h-4 w-24 rounded bg-gray-200" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function PricingPage({
  report,
  facts = [],
  factsLoading,
  factsError,
}: PricingPageProps) {
  const [search, setSearch] = useState('')
  const [entityFilter, setEntityFilter] = useState('all')
  const [tierFilter, setTierFilter] = useState<TierFilter>('all')
  const [safeFilter, setSafeFilter] = useState<SafeFilter>('all')
  const [domainFilter, setDomainFilter] = useState('all')
  const [sortMode, setSortMode] = useState<SortMode>('confidence_desc')

  // Live Pricing-Pressure facts only
  const pricingFacts = useMemo(
    () => facts.filter(fact => fact.signal_type === 'pricing_pressure'),
    [facts]
  )

  // Derived Filter Options
  const entityOptions = useMemo(() => {
    const liveEntities = Array.from(new Set(pricingFacts.map(f => f.entity).filter(Boolean)))
    return Array.from(new Set(['all', 'Nvidia', 'AMD', 'Supermicro', 'market', ...liveEntities]))
  }, [pricingFacts])

  const domainOptions = useMemo(() => {
    const domains = Array.from(new Set(pricingFacts.map(f => sourceDomain(f.source_url)).filter(Boolean)))
    return ['all', ...domains.sort()]
  }, [pricingFacts])

  // Summary statistics
  const summary = useMemo(() => {
    const safeCount = pricingFacts.filter(f => f.safe_verified).length
    const uniqueDomains = new Set(pricingFacts.map(f => sourceDomain(f.source_url))).size
    const highCredCount = pricingFacts.filter(f => f.source_tier <= 2).length
    return {
      total: pricingFacts.length,
      safe: safeCount,
      domains: uniqueDomains,
      highCred: highCredCount,
    }
  }, [pricingFacts])

  // Filtered pricing facts
  const filteredFacts = useMemo(() => {
    const searchText = search.trim().toLowerCase()
    const matching = pricingFacts.filter(fact => {
      if (searchText && !normalizedText(fact).includes(searchText)) return false
      if (entityFilter !== 'all' && fact.entity.toLowerCase() !== entityFilter.toLowerCase()) return false
      if (tierFilter !== 'all' && fact.source_tier !== Number(tierFilter)) return false
      if (safeFilter === 'safe_only' && !fact.safe_verified) return false
      if (domainFilter !== 'all' && sourceDomain(fact.source_url).toLowerCase() !== domainFilter.toLowerCase()) return false
      return true
    })
    return sortFacts(matching, sortMode)
  }, [pricingFacts, search, entityFilter, tierFilter, safeFilter, domainFilter, sortMode])

  // Provider Reliability Table
  const providerSummary = useMemo(() => {
    const map = new Map<string, { count: number; bestTier: number; totalConf: number }>()
    pricingFacts.forEach(fact => {
      const domain = sourceDomain(fact.source_url)
      const existing = map.get(domain)
      if (existing) {
        existing.count += 1
        existing.bestTier = Math.min(existing.bestTier, fact.source_tier)
        existing.totalConf += fact.confidence
      } else {
        map.set(domain, {
          count: 1,
          bestTier: fact.source_tier,
          totalConf: fact.confidence,
        })
      }
    })
    return Array.from(map.entries()).map(([domain, stats]) => ({
      domain,
      count: stats.count,
      bestTier: stats.bestTier,
      avgConfidence: stats.totalConf / stats.count,
    })).sort((a, b) => b.count - a.count)
  }, [pricingFacts])

  function clearFilters() {
    setSearch('')
    setEntityFilter('all')
    setTierFilter('all')
    setSafeFilter('all')
    setDomainFilter('all')
    setSortMode('confidence_desc')
  }

  // 1. Loading state
  if (factsLoading) {
    return (
      <section className="flex flex-col gap-6">
        <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
          <p className="text-sm text-gray-400">Loading pricing intelligence evidence...</p>
        </div>
        <PricingSkeleton />
      </section>
    )
  }

  // 2. Error state
  if (factsError) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-600" />
        <h3 className="mt-3 text-lg font-bold text-red-950">Pricing intelligence load failed</h3>
        <p className="mt-2 text-sm leading-relaxed text-red-700">
          The FastAPI backend report facts endpoint returned an error. Stale fallback data is disabled for data trustworthiness.
        </p>
        <p className="mt-3 font-mono text-xs text-red-600 bg-red-100/50 inline-block px-3 py-1 rounded-lg">
          {factsError.message}
        </p>
      </section>
    )
  }

  // 3. No report loaded or empty pricing facts
  if (!report) return null

  if (pricingFacts.length === 0) {
    return (
      <section className="flex flex-col gap-6">
        <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <TrendingDown className="mx-auto h-10 w-10 text-gray-300" />
          <h3 className="mt-3 text-lg font-bold text-gray-900">No pricing-pressure facts found</h3>
          <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
            The latest report is loaded, but it does not contain any evidence labeled with the <span className="font-semibold">pricing_pressure</span> signal type.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              to="/workspace/evidence"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
            >
              Open Evidence Explorer
            </Link>
            <Link
              to="/chat?context=pricing"
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Consult AI Chat
            </Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-6" id="pricing-intelligence-workspace">
      {/* Header section */}
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800">
                GPU Pricing Pressure
              </span>
              <span className="text-xs text-slate-400">Grounded Intelligence</span>
            </div>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-gray-950">Pricing Intelligence</h2>
            <p className="mt-3 max-w-3xl text-base leading-relaxed text-gray-600">
              Live evidence-backed facts on cloud hardware pricing pressure, GPU rental rates, and semiconductor wholesale margins.
            </p>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow transition-shadow">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total pricing facts</p>
          <p className="mt-2 text-3xl font-bold text-gray-950">{summary.total}</p>
          <p className="mt-1.5 text-xs text-gray-500">Live pricing pressure markers</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow transition-shadow">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">SAFE-verified facts</p>
          <p className="mt-2 text-3xl font-bold text-emerald-700">{summary.safe}</p>
          <p className="mt-1.5 text-xs text-emerald-600 font-medium">Atomic claims verified</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow transition-shadow">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Unique source domains</p>
          <p className="mt-2 text-3xl font-bold text-blue-700">{summary.domains}</p>
          <p className="mt-1.5 text-xs text-gray-500">Independent publishers</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow transition-shadow">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tier 1/2 pricing facts</p>
          <p className="mt-2 text-3xl font-bold text-gray-950">{summary.highCred}</p>
          <p className="mt-1.5 text-xs text-gray-500">High-credibility journals</p>
        </div>
      </div>

      {/* Controls / Filter section */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {/* Search */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Search</span>
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <input
                id="pricing-search-input"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Product, quote, company..."
                className="h-10 w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 text-sm text-gray-700 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
              />
            </div>
          </label>

          {/* Entity Filter */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Company</span>
            <select
              id="pricing-entity-select"
              value={entityFilter}
              onChange={e => setEntityFilter(e.target.value)}
              className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
            >
              {entityOptions.map(ent => (
                <option key={ent} value={ent}>
                  {ent === 'all' ? 'All Companies' : ent}
                </option>
              ))}
            </select>
          </label>

          {/* Tier Filter */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Source Tier</span>
            <select
              id="pricing-tier-select"
              value={tierFilter}
              onChange={e => setTierFilter(e.target.value as TierFilter)}
              className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
            >
              <option value="all">All Tiers</option>
              <option value="1">Tier 1 (Premium Journals)</option>
              <option value="2">Tier 2 (Reputable Tech)</option>
              <option value="3">Tier 3 (Blogs & Analysis)</option>
              <option value="4">Tier 4 (Unverified / Social)</option>
            </select>
          </label>

          {/* SAFE Filter */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">SAFE verified</span>
            <select
              id="pricing-safe-select"
              value={safeFilter}
              onChange={e => setSafeFilter(e.target.value as SafeFilter)}
              className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
            >
              <option value="all">All Facts</option>
              <option value="safe_only">SAFE Only</option>
            </select>
          </label>

          {/* Domain Filter */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Source Domain</span>
            <select
              id="pricing-domain-select"
              value={domainFilter}
              onChange={e => setDomainFilter(e.target.value)}
              className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
            >
              {domainOptions.map(dom => (
                <option key={dom} value={dom}>
                  {dom === 'all' ? 'All Domains' : dom}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* Sort & Matching Stats */}
        <div className="mt-4 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex flex-row items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 whitespace-nowrap">Sort by</span>
            <select
              id="pricing-sort-select"
              value={sortMode}
              onChange={e => setSortMode(e.target.value as SortMode)}
              className="h-9 rounded-lg border border-gray-300 bg-white px-3 text-xs text-gray-700 focus:border-blue-500 focus:outline-none transition-all"
            >
              <option value="confidence_desc">Confidence Descending</option>
              <option value="tier_asc">Source Tier Ascending</option>
              <option value="newest">Newest Published Date</option>
              <option value="source_domain">Source Domain A-Z</option>
            </select>
          </label>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-slate-600">
              {filteredFacts.length} matching {filteredFacts.length === 1 ? 'fact' : 'facts'}
            </span>
            {(search || entityFilter !== 'all' || tierFilter !== 'all' || safeFilter !== 'all' || domainFilter !== 'all') && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 hover:text-gray-900 transition-all shadow-sm"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="grid gap-6 lg:grid-cols-[1.8fr_1fr]">
        {/* Left Side: Facts Cards */}
        <div className="flex flex-col gap-4">
          {filteredFacts.length === 0 ? (
            <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
              <TrendingDown className="mx-auto h-10 w-10 text-gray-300" />
              <h4 className="mt-3 text-base font-bold text-gray-900">No matching pricing facts</h4>
              <p className="mt-2 text-sm text-gray-500">
                Try adjusting your filters or resetting the search query to see the pricing pressure evidence.
              </p>
              <button
                type="button"
                onClick={clearFilters}
                className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
              >
                Reset all filters
              </button>
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredFacts.map(fact => (
                <PricingFactCard key={fact.fact_id} fact={fact} />
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Sidebar Tables & CTAs */}
        <div className="flex flex-col gap-6">
          {/* Provider Summary Table */}
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
              <Layers className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-bold text-gray-950 uppercase tracking-wide">
                Source Coverage & Reliability
              </h3>
            </div>
            <p className="mt-2 text-xs text-gray-500 leading-normal">
              Aggregated credibility statistics for each publisher domain representing GPU pricing facts.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-200 text-slate-400 font-semibold uppercase tracking-wider">
                    <th className="pb-2">Domain</th>
                    <th className="pb-2 text-center">Facts</th>
                    <th className="pb-2 text-center">Best Tier</th>
                    <th className="pb-2 text-right">Avg Conf</th>
                  </tr>
                </thead>
                <tbody>
                  {providerSummary.map(row => (
                    <tr key={row.domain} className="border-b border-gray-50 last:border-0 hover:bg-slate-50/50 transition-colors">
                      <td className="py-2.5 font-semibold text-slate-800 max-w-[140px] truncate">{row.domain}</td>
                      <td className="py-2.5 text-center font-medium tabular-nums text-slate-700">{row.count}</td>
                      <td className="py-2.5 text-center">
                        <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                          T{row.bestTier}
                        </span>
                      </td>
                      <td className="py-2.5 text-right font-medium tabular-nums text-slate-700">
                        {(row.avgConfidence * 100).toFixed(0)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* CTA Blocks */}
          <div className="flex flex-col gap-4">
            {/* View Evidence Explorer */}
            <article className="rounded-2xl border border-gray-200 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 p-5 shadow-sm hover:shadow-md transition-shadow">
              <h4 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                <Layers className="h-4 w-4 text-blue-600" />
                Cross-Signal Evidence Explorer
              </h4>
              <p className="mt-2 text-xs leading-relaxed text-gray-600">
                Explore hiring momentum, strategic product launches, and developer adoption indicators across all signal types in the latest report.
              </p>
              <Link
                to="/workspace/evidence"
                className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700 group"
              >
                Explore all evidence
                <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </article>

            {/* Consult AI Chat */}
            <article className="rounded-2xl border border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50 p-5 shadow-sm hover:shadow-md transition-shadow">
              <h4 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-indigo-600 animate-pulse" />
                Ask PulseLens AI
              </h4>
              <p className="mt-2 text-xs leading-relaxed text-gray-600">
                Ask deep-reasoning questions about retail markups, specific hardware margins, or supplier pricing changes.
              </p>
              <Link
                to="/chat?context=pricing"
                className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-700 group"
              >
                Consult chat assistant
                <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </article>

            {/* Review Signals */}
            <article className="rounded-2xl border border-gray-200 bg-gradient-to-r from-emerald-50/30 to-teal-50/30 p-5 shadow-sm hover:shadow-md transition-shadow">
              <h4 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                <TrendingDown className="h-4 w-4 text-emerald-600" />
                Review Score Contribution
              </h4>
              <p className="mt-2 text-xs leading-relaxed text-gray-600">
                Examine raw score contributions and contradictions surfaced across the semiconductor supply chain.
              </p>
              <Link
                to="/workspace/signals"
                className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-emerald-600 hover:text-emerald-700 group"
              >
                Open signal dashboard
                <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </article>
          </div>
        </div>
      </div>
    </section>
  )
}
