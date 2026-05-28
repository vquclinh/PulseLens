import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { FactObject, MarketPulseReport, SignalType } from '@/types/api'
import { formatDate } from '@/lib/utils'
import MomentumBadge from '@/shared/components/momentum-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import TierBadge from '@/shared/components/tier-badge'
import {
  ShieldCheck, Copy, Check, ExternalLink, MessageSquare,
  AlertTriangle, ArrowRight, BarChart2, Building2, Layers
} from 'lucide-react'

interface CompaniesPageProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
  factsError: Error | null
}

const SIGNAL_LABELS: Record<SignalType, string> = {
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  investor_signal: 'Investor Signal',
  strategic_messaging: 'Strategic Messaging',
  supplier_risk: 'Supplier Risk',
  news_sentiment: 'News Sentiment',
  hiring_momentum: 'Hiring Momentum',
}

const SIGNAL_COLORS: Record<SignalType, string> = {
  product_launch: 'bg-blue-500',
  pricing_pressure: 'bg-amber-500',
  investor_signal: 'bg-purple-500',
  strategic_messaging: 'bg-indigo-500',
  supplier_risk: 'bg-red-500',
  news_sentiment: 'bg-teal-500',
  hiring_momentum: 'bg-emerald-500',
}

const SIGNAL_ORDER: SignalType[] = [
  'product_launch', 'pricing_pressure', 'investor_signal',
  'strategic_messaging', 'supplier_risk', 'news_sentiment', 'hiring_momentum',
]

const POSITION_STYLES: Record<string, { bg: string; text: string }> = {
  gaining: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  holding: { bg: 'bg-blue-50',    text: 'text-blue-700' },
  losing:  { bg: 'bg-red-50',     text: 'text-red-700' },
}

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

/** Strip inline citation IDs like [claim_xxx] or [fact_xxx] from display text only. Never mutates data. */
function stripIds(text: string): string {
  return text
    .replace(/\[(?:claim|fact)_[a-z0-9_-]+\]/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

/** Conservative entity → company matching. Does NOT map 'market' to any company. */
function matchEntity(entity: string, companyName: string, ticker: string): boolean {
  const e = entity.trim().toLowerCase()
  const c = companyName.trim().toLowerCase()
  const t = ticker.trim().toLowerCase()
  if (e === 'market' || e === 'industry' || e === 'sector') return false
  return e === c || e === t || c.startsWith(e) || e.startsWith(c)
}

function publishedTime(f: FactObject): number {
  if (!f.published_date) return 0
  const p = Date.parse(f.published_date)
  return Number.isFinite(p) ? p : 0
}

// ---------- sub-components ----------

function EvidenceCard({ fact }: { fact: FactObject }) {
  const [copied, setCopied] = useState(false)
  function copyQuote() {
    void navigator.clipboard?.writeText(fact.evidence_quote)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-200 hover:shadow transition-all">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
          {SIGNAL_LABELS[fact.signal_type] ?? fact.signal_type}
        </span>
        {fact.safe_verified && (
          <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            <ShieldCheck className="h-3 w-3" /> SAFE
          </span>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          <TierBadge tier={fact.source_tier} />
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>
      <p className="mt-3 text-sm font-semibold leading-snug text-gray-950">{stripIds(fact.claim)}</p>
      <blockquote className="mt-3 border-l-4 border-blue-200 bg-slate-50/40 py-2 pl-3 pr-2 text-sm leading-relaxed italic text-gray-700">
        "{stripIds(fact.evidence_quote)}"
      </blockquote>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 pt-3 text-xs text-gray-500">
        <span className="font-semibold text-gray-700">{sourceDomain(fact.source_url)}</span>
        <span>{formatDate(fact.published_date) || 'Date unavailable'}</span>
        <span className="font-medium tabular-nums">{(fact.confidence * 100).toFixed(0)}% conf</span>
        <span className="font-mono text-[10px] text-gray-400">{fact.fact_id.substring(0, 10)}</span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button type="button" onClick={copyQuote}
          className="flex items-center gap-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">
          {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
        <a href={fact.source_url} target="_blank" rel="noreferrer"
          className="flex items-center gap-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">
          <ExternalLink className="h-3 w-3" /> Source
        </a>
        <Link to={`/chat?context=fact&fact_id=${fact.fact_id}`}
          className="ml-auto flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
          <MessageSquare className="h-3 w-3" /> Ask Chat
        </Link>
      </div>
    </article>
  )
}

export default function CompaniesPage({ report, facts = [], factsLoading, factsError }: CompaniesPageProps) {
  const [selectedCompany, setSelectedCompany] = useState<string>('all')

  // Build per-company fact groups using conservative matching
  const companyFactMap = useMemo(() => {
    const map = new Map<string, FactObject[]>()
    for (const narrative of report.company_narratives) {
      map.set(narrative.company, facts.filter(f => matchEntity(f.entity, narrative.company, narrative.ticker)))
    }
    return map
  }, [facts, report.company_narratives])

  // Derive company enrichment from facts
  const companyStats = useMemo(() => {
    return report.company_narratives.map(n => {
      const cFacts = companyFactMap.get(n.company) ?? []
      const safeCount = cFacts.filter(f => f.safe_verified).length
      const domains = new Set(cFacts.map(f => sourceDomain(f.source_url))).size
      const signalCounts: Partial<Record<SignalType, number>> = {}
      for (const f of cFacts) signalCounts[f.signal_type] = (signalCounts[f.signal_type] ?? 0) + 1
      const topSignal = Object.entries(signalCounts).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))[0]?.[0] as SignalType | undefined
      const avgConf = cFacts.length > 0 ? cFacts.reduce((s, f) => s + f.confidence, 0) / cFacts.length : null
      const latestDate = cFacts.reduce<string | null>((best, f) => {
        if (!f.published_date) return best
        if (!best || f.published_date > best) return f.published_date
        return best
      }, null)
      return { narrative: n, cFacts, safeCount, domains, signalCounts, topSignal, avgConf, latestDate }
    })
  }, [report.company_narratives, companyFactMap])

  // All company names for selector
  const companyNames = report.company_narratives.map(n => n.company)

  // Evidence for selected company / all — track total matching for count display
  const { evidenceFacts, evidenceTotalCount } = useMemo(() => {
    if (selectedCompany === 'all') {
      const sorted = [...facts].sort((a, b) => b.confidence - a.confidence)
      return { evidenceFacts: sorted.slice(0, 8), evidenceTotalCount: sorted.length }
    }
    const narrative = report.company_narratives.find(n => n.company === selectedCompany)
    if (!narrative) return { evidenceFacts: [], evidenceTotalCount: 0 }
    const all = (companyFactMap.get(narrative.company) ?? []).sort((a, b) => b.confidence - a.confidence)
    return { evidenceFacts: all.slice(0, 8), evidenceTotalCount: all.length }
  }, [selectedCompany, facts, companyFactMap, report.company_narratives])

  // Quick insight cards — derived from companyStats, no hardcoded values
  const insights = useMemo(() => {
    if (companyStats.length === 0) return []
    const byFacts = [...companyStats].sort((a, b) => b.cFacts.length - a.cFacts.length)
    const byPricing = [...companyStats].sort((a, b) =>
      (b.signalCounts.pricing_pressure ?? 0) - (a.signalCounts.pricing_pressure ?? 0)
    )
    const byProduct = [...companyStats].sort((a, b) =>
      (b.signalCounts.product_launch ?? 0) - (a.signalCounts.product_launch ?? 0)
    )
    const result: { label: string; value: string; sub: string }[] = []
    if (byFacts[0] && byFacts[0].cFacts.length > 0) {
      result.push({ label: 'Most evidence', value: byFacts[0].narrative.company, sub: `${byFacts[0].cFacts.length} facts` })
    }
    if (byPricing[0] && (byPricing[0].signalCounts.pricing_pressure ?? 0) > 0) {
      result.push({ label: 'Pricing pressure', value: byPricing[0].narrative.company, sub: `${byPricing[0].signalCounts.pricing_pressure} facts` })
    }
    if (byProduct[0] && (byProduct[0].signalCounts.product_launch ?? 0) > 0) {
      result.push({ label: 'Product momentum', value: byProduct[0].narrative.company, sub: `${byProduct[0].signalCounts.product_launch} facts` })
    }
    return result
  }, [companyStats])

  // --- States ---
  if (factsLoading) {
    return (
      <section className="flex flex-col gap-6">
        <div className="animate-pulse rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
          <div className="h-6 w-48 rounded bg-gray-200" />
          <div className="mt-3 h-4 w-96 rounded bg-gray-100" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="h-5 w-32 rounded bg-gray-200" /><div className="mt-3 h-16 w-full rounded bg-gray-100" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  if (factsError) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-500" />
        <h3 className="mt-3 text-base font-bold text-red-950">Company data load failed</h3>
        <p className="mt-2 text-sm text-red-700">{factsError.message}</p>
      </section>
    )
  }

  if (report.company_narratives.length === 0) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-sm">
        <Building2 className="mx-auto h-10 w-10 text-gray-300" />
        <h3 className="mt-3 text-base font-bold text-gray-900">No company narratives in this report</h3>
        <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
          The pipeline did not produce company narratives for this run.
        </p>
        <Link to="/workspace/evidence"
          className="mt-5 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          Open Evidence Explorer <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-6" id="company-lens-workspace">

      {/* Header */}
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Company Lens</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-gray-950">Company Lens</h2>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-gray-600">
              Compare company momentum, risks, and evidence from the latest report.
              All metrics are derived from live <span className="font-mono text-sm bg-slate-100 px-1 rounded">/api/report/{report.report_id}/facts</span>.
            </p>
            <p className="mt-3 text-xs text-gray-400 max-w-2xl">
              Company reads are synthesized from the latest report. Evidence counts and signal distributions are computed from source-backed facts.
            </p>
          </div>
          <span className="shrink-0 font-mono text-xs text-gray-400">
            Report: <span className="font-semibold text-gray-600">{report.report_id}</span>
          </span>
        </div>

        {/* Quick insight summary chips — derived from live companyStats */}
        {insights.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-3 border-t border-gray-100 pt-5">
            {insights.map(ins => (
              <div key={ins.label} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">{ins.label}:</span>
                <span className="text-sm font-bold text-gray-900">{ins.value}</span>
                <span className="rounded-full bg-white border border-gray-200 px-2 py-0.5 text-xs font-medium text-gray-500">{ins.sub}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Company selector */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCompany('all')}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${selectedCompany === 'all' ? 'bg-blue-600 text-white shadow-sm' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}
        >All Companies</button>
        {companyNames.map(name => (
          <button key={name}
            onClick={() => setSelectedCompany(name)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${selectedCompany === name ? 'bg-blue-600 text-white shadow-sm' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}
          >{name}</button>
        ))}
      </div>

      {/* Company cards grid */}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {companyStats
          .filter(s => selectedCompany === 'all' || s.narrative.company === selectedCompany)
          .map(({ narrative: n, cFacts, safeCount, domains, signalCounts, topSignal, avgConf, latestDate }) => {
            const pos = POSITION_STYLES[n.competitive_position] ?? POSITION_STYLES.holding
            const isSelected = selectedCompany === n.company
            return (
              <article key={n.ticker}
                className={`rounded-2xl border bg-white p-6 shadow-sm transition-all ${isSelected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200 hover:border-blue-200 hover:shadow-md'}`}
              >
                {/* Company header */}
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-100">
                    <span className="text-sm font-bold text-blue-700">{n.company.slice(0, 2).toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-base font-bold text-gray-950">{n.company}</span>
                      <span className="font-mono text-xs text-gray-500">{n.ticker}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      <MomentumBadge momentum={n.momentum} />
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${pos.bg} ${pos.text}`}>
                        {n.competitive_position}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Narrative */}
                <p className="mt-4 text-sm leading-relaxed text-gray-600 line-clamp-3">{stripIds(n.narrative)}</p>

                {/* Key drivers */}
                {n.key_drivers.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {n.key_drivers.slice(0, 4).map((d, i) => (
                      <span key={i} className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">{stripIds(d)}</span>
                    ))}
                  </div>
                )}

                {/* Stats row */}
                <div className="mt-4 grid grid-cols-4 gap-2 border-t border-gray-100 pt-4 text-center text-xs">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Facts</p>
                    <p className="mt-1 text-base font-bold text-gray-900">{cFacts.length}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">SAFE</p>
                    <p className="mt-1 text-base font-bold text-emerald-700">{safeCount}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Domains</p>
                    <p className="mt-1 text-base font-bold text-gray-900">{domains}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Avg Conf</p>
                    <p className="mt-1 text-base font-bold text-gray-900">
                      {avgConf !== null ? `${(avgConf * 100).toFixed(0)}%` : '—'}
                    </p>
                  </div>
                </div>

                {/* Signal distribution bars */}
                {cFacts.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {SIGNAL_ORDER.filter(sig => (signalCounts[sig] ?? 0) > 0).slice(0, 5).map(sig => {
                      const count = signalCounts[sig] ?? 0
                      const pct = Math.round((count / cFacts.length) * 100)
                      return (
                        <div key={sig} className="flex items-center gap-2">
                          <span className="w-[130px] shrink-0 text-xs text-gray-500 truncate">{SIGNAL_LABELS[sig]}</span>
                          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${SIGNAL_COLORS[sig]}`} style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-6 text-right text-xs tabular-nums font-medium text-gray-600">{count}</span>
                        </div>
                      )
                    })}
                  </div>
                )}

                {cFacts.length === 0 && (
                  <p className="mt-4 text-xs text-gray-400 italic">No direct evidence facts for this company in the latest report.</p>
                )}

                {/* Latest date */}
                {latestDate && (
                  <p className="mt-3 text-[10px] text-gray-400">Latest evidence: {formatDate(latestDate)}</p>
                )}

                {/* CTAs */}
                <div className="mt-4 flex gap-2 border-t border-gray-100 pt-4">
                  <button
                    onClick={() => setSelectedCompany(n.company)}
                    className="flex-1 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition-colors text-center"
                  >
                    View evidence
                  </button>
                  <Link to={`/chat?context=company&company=${encodeURIComponent(n.company)}`}
                    className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
                    <MessageSquare className="h-3 w-3" /> Ask Chat
                  </Link>
                </div>
              </article>
            )
          })}
      </div>

      {/* Comparison table */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <BarChart2 className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold uppercase tracking-wide text-gray-950">Company Comparison</h3>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-200 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="pb-2 pr-4">Company</th>
                <th className="pb-2 pr-4">Momentum</th>
                <th className="pb-2 pr-4 text-center">Facts</th>
                <th className="pb-2 pr-4 text-center">SAFE</th>
                <th className="pb-2 pr-4">Top Signal</th>
                <th className="pb-2 pr-4 text-center">Avg Conf</th>
                <th className="pb-2 pr-4 text-center">Domains</th>
                <th className="pb-2 pr-4">Latest</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {companyStats.map(({ narrative: n, cFacts, safeCount, domains, topSignal, avgConf, latestDate }) => (
                <tr key={n.ticker}
                  className={`border-b border-gray-50 last:border-0 cursor-pointer hover:bg-blue-50/30 transition-colors ${selectedCompany === n.company ? 'bg-blue-50/50' : ''}`}
                  onClick={() => setSelectedCompany(selectedCompany === n.company ? 'all' : n.company)}
                >
                  <td className="py-3 pr-4 font-bold text-gray-900">
                    {n.company} <span className="font-mono font-normal text-gray-400">({n.ticker})</span>
                  </td>
                  <td className="py-3 pr-4"><MomentumBadge momentum={n.momentum} /></td>
                  <td className="py-3 pr-4 text-center font-medium tabular-nums text-gray-800">{cFacts.length}</td>
                  <td className="py-3 pr-4 text-center font-medium tabular-nums text-emerald-700">{safeCount}</td>
                  <td className="py-3 pr-4 text-gray-700">
                    {topSignal ? SIGNAL_LABELS[topSignal] : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="py-3 pr-4 text-center tabular-nums text-gray-700">
                    {avgConf !== null ? `${(avgConf * 100).toFixed(0)}%` : '—'}
                  </td>
                  <td className="py-3 pr-4 text-center tabular-nums text-gray-700">{domains}</td>
                  <td className="py-3 pr-4 text-gray-500">{latestDate ? formatDate(latestDate) : '—'}</td>
                  <td className="py-3">
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); setSelectedCompany(selectedCompany === n.company ? 'all' : n.company) }}
                      className="whitespace-nowrap rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
                    >
                      Inspect →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-400">Click a row or <strong>Inspect →</strong> to filter the evidence preview below. Fact counts are derived from live report facts only.</p>
      </section>

      {/* Evidence preview */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Layers className="h-4 w-4 text-blue-600 shrink-0" />
            <h3 className="text-sm font-bold uppercase tracking-wide text-gray-950">
              Evidence Preview
            </h3>
            <span className="text-sm font-semibold text-blue-600">
              · {selectedCompany === 'all' ? 'All Companies' : selectedCompany}
            </span>
            {evidenceTotalCount > 0 && (
              <span className="text-xs text-gray-400">
                · Showing {evidenceFacts.length} of {evidenceTotalCount} facts
              </span>
            )}
          </div>
          {selectedCompany !== 'all' && (
            <button onClick={() => setSelectedCompany('all')}
              className="ml-2 shrink-0 rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
              Clear filter ×
            </button>
          )}
        </div>

        {evidenceFacts.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-sm text-gray-500">
              {selectedCompany !== 'all'
                ? `No direct evidence facts for ${selectedCompany} in the latest report.`
                : 'No evidence facts loaded yet.'}
            </p>
          </div>
        ) : (
          <>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {evidenceFacts.map(fact => <EvidenceCard key={fact.fact_id} fact={fact} />)}
            </div>
            <div className="mt-4 flex justify-end">
              <Link to="/workspace/evidence"
                className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700">
                View all evidence <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </>
        )}
      </section>

      {/* CTAs */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Link to="/workspace/evidence"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50/60 to-indigo-50/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Evidence Explorer</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">Inspect all signal types across all companies.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-600">
            Open <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
        <Link to="/workspace/signals"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-emerald-50/40 to-teal-50/40 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Signal Radar</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">Review score contributions and market-wide signal patterns.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
            Review signals <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
        <Link to="/chat?context=report"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-slate-50 to-gray-50 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Ask PulseLens AI</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">Ask deep-reasoning questions about specific companies and signals.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-indigo-600">
            Ask Chat <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
      </div>
    </section>
  )
}
