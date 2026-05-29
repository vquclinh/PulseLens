import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { FactObject, MarketPulseReport, SignalType } from '@/types/api'
import { formatDate } from '@/lib/utils'
import SentimentBadge from '@/shared/components/sentiment-badge'
import TierBadge from '@/shared/components/tier-badge'
import {
  ShieldCheck, Copy, Check, ExternalLink, MessageSquare,
  AlertTriangle, ArrowRight, Activity, Radar, Layers
} from 'lucide-react'

interface SignalsPageProps {
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

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

function stripIds(text: string): string {
  return text
    .replace(/\[(?:claim|fact)_[a-z0-9_-]+\]/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

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
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
          {fact.entity}
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

export default function SignalsPage({ report, facts = [], factsLoading, factsError }: SignalsPageProps) {
  const [selectedSignal, setSelectedSignal] = useState<SignalType | 'all'>('all')

  const signalStats = useMemo(() => {
    const activeSignals = new Set<SignalType>()
    report.top_signals.forEach(ts => activeSignals.add(ts.signal_type))
    facts.forEach(f => activeSignals.add(f.signal_type))

    return Array.from(activeSignals).map(sig => {
      const sFacts = facts.filter(f => f.signal_type === sig)
      const safeCount = sFacts.filter(f => f.safe_verified).length
      const domains = new Set(sFacts.map(f => sourceDomain(f.source_url))).size
      
      const entityCounts: Record<string, number> = {}
      sFacts.forEach(f => {
        const e = f.entity.trim()
        entityCounts[e] = (entityCounts[e] ?? 0) + 1
      })
      const topEntity = Object.entries(entityCounts).sort((a, b) => b[1] - a[1])[0]?.[0]
      
      const avgConf = sFacts.length > 0 ? sFacts.reduce((acc, f) => acc + f.confidence, 0) / sFacts.length : null
      
      const sentCounts = { positive: 0, negative: 0, neutral: 0 }
      sFacts.forEach(f => sentCounts[f.sentiment]++)

      const scoreContribution = report.signal_breakdown?.[sig] ?? null
      const narrative = report.top_signals.find(ts => ts.signal_type === sig)?.narrative ?? null

      return {
        signal: sig,
        sFacts,
        safeCount,
        domains,
        topEntity,
        avgConf,
        sentCounts,
        scoreContribution,
        narrative
      }
    }).sort((a, b) => (b.scoreContribution ?? 0) - (a.scoreContribution ?? 0) || b.sFacts.length - a.sFacts.length)
  }, [report, facts])

  const evidenceFacts = useMemo(() => {
    if (selectedSignal === 'all') {
      const sorted = [...facts].sort((a, b) => b.confidence - a.confidence)
      return { preview: sorted.slice(0, 8), total: sorted.length }
    }
    const filtered = facts.filter(f => f.signal_type === selectedSignal).sort((a, b) => b.confidence - a.confidence)
    return { preview: filtered.slice(0, 8), total: filtered.length }
  }, [selectedSignal, facts])

  const selectedSignalData = useMemo(() => {
    if (selectedSignal === 'all') return null
    return signalStats.find(s => s.signal === selectedSignal) ?? null
  }, [selectedSignal, signalStats])

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
        <h3 className="mt-3 text-base font-bold text-red-950">Signal data load failed</h3>
        <p className="mt-2 text-sm text-red-700">{factsError.message}</p>
      </section>
    )
  }

  if (facts.length === 0 && report.top_signals.length === 0) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-sm">
        <Radar className="mx-auto h-10 w-10 text-gray-300" />
        <h3 className="mt-3 text-base font-bold text-gray-900">No signals in this report</h3>
        <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
          The pipeline did not detect any significant market signals.
        </p>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-6" id="signal-radar-workspace">
      {/* Header */}
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Signal Radar</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-gray-950">Signal Radar</h2>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-gray-600">
              Evidence-backed signal drilldown from the latest report.
            </p>
            <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/50 p-3 max-w-2xl">
              <p className="text-xs text-indigo-800 leading-relaxed">
                <strong>Trust Note:</strong> Evidence counts are computed directly from source-backed facts. 
                Signal scores are normalized report contributions and should not be read as fact counts.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Signal selector */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedSignal('all')}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${selectedSignal === 'all' ? 'bg-blue-600 text-white shadow-sm' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}
        >All Signals</button>
        {signalStats.map(stat => (
          <button key={stat.signal}
            onClick={() => setSelectedSignal(stat.signal)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${selectedSignal === stat.signal ? 'bg-blue-600 text-white shadow-sm' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}
          >{SIGNAL_LABELS[stat.signal]}</button>
        ))}
      </div>

      {/* Signal Detail Panel or Summary Cards */}
      {selectedSignalData ? (
        <article className="rounded-2xl border border-blue-200 bg-white p-7 shadow-md ring-1 ring-blue-50">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <div className={`h-3 w-3 rounded-full ${SIGNAL_COLORS[selectedSignalData.signal]}`} />
                <h3 className="text-xl font-bold text-gray-900">{SIGNAL_LABELS[selectedSignalData.signal]}</h3>
                {selectedSignalData.scoreContribution !== null && (
                  <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                    Score: {selectedSignalData.scoreContribution.toFixed(1)}
                  </span>
                )}
              </div>
              {selectedSignalData.narrative && (
                <p className="mt-4 text-sm leading-relaxed text-gray-700 max-w-3xl">
                  {stripIds(selectedSignalData.narrative)}
                </p>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4 lg:shrink-0 lg:grid-cols-4">
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-center min-w-[100px]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Evidence</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{selectedSignalData.sFacts.length}</p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-emerald-50/50 p-4 text-center min-w-[100px]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">SAFE</p>
                <p className="mt-1 text-2xl font-bold text-emerald-700">{selectedSignalData.safeCount}</p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-center min-w-[100px]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Domains</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{selectedSignalData.domains}</p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-center min-w-[100px]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Avg Conf</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {selectedSignalData.avgConf !== null ? `${(selectedSignalData.avgConf * 100).toFixed(0)}%` : '—'}
                </p>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-gray-100 pt-5 text-sm">
            <div className="flex items-center gap-2 text-gray-600">
              <span className="font-semibold">Top Entity:</span>
              <span>{selectedSignalData.topEntity ?? '—'}</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <span className="font-semibold">Sentiment:</span>
              <div className="flex gap-1.5 text-xs font-medium">
                <span className="text-emerald-600">{selectedSignalData.sentCounts.positive} pos</span>
                <span className="text-gray-400">·</span>
                <span className="text-gray-500">{selectedSignalData.sentCounts.neutral} neu</span>
                <span className="text-gray-400">·</span>
                <span className="text-red-600">{selectedSignalData.sentCounts.negative} neg</span>
              </div>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Link to="/workspace/evidence" className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                Evidence Explorer
              </Link>
              <Link to={`/chat?context=signal&signal=${selectedSignalData.signal}`} className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                <MessageSquare className="h-3 w-3" /> Ask Chat
              </Link>
            </div>
          </div>
        </article>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {signalStats.map(stat => (
            <article key={stat.signal}
              className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:border-blue-200 hover:shadow-md transition-all cursor-pointer"
              onClick={() => setSelectedSignal(stat.signal)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className={`h-2.5 w-2.5 rounded-full ${SIGNAL_COLORS[stat.signal]}`} />
                  <h3 className="text-base font-bold text-gray-900">{SIGNAL_LABELS[stat.signal]}</h3>
                </div>
                {stat.scoreContribution !== null && (
                  <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700">
                    Score: {stat.scoreContribution.toFixed(1)}
                  </span>
                )}
              </div>
              
              <div className="mt-4 grid grid-cols-4 gap-2 border-t border-gray-100 pt-4 text-center text-xs">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Facts</p>
                  <p className="mt-1 text-base font-bold text-gray-900">{stat.sFacts.length}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">SAFE</p>
                  <p className="mt-1 text-base font-bold text-emerald-700">{stat.safeCount}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Domains</p>
                  <p className="mt-1 text-base font-bold text-gray-900">{stat.domains}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Avg Conf</p>
                  <p className="mt-1 text-base font-bold text-gray-900">
                    {stat.avgConf !== null ? `${(stat.avgConf * 100).toFixed(0)}%` : '—'}
                  </p>
                </div>
              </div>
              
              <div className="mt-4 flex flex-col gap-1.5 text-xs text-gray-500">
                <div className="flex justify-between">
                  <span>Top Entity:</span>
                  <span className="font-semibold text-gray-700">{stat.topEntity ?? '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Sentiment:</span>
                  <span className="font-semibold text-gray-700">
                    <span className="text-emerald-600">{stat.sentCounts.positive}</span> / {stat.sentCounts.neutral} / <span className="text-red-600">{stat.sentCounts.negative}</span>
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Comparison table */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <Activity className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold uppercase tracking-wide text-gray-950">Signal Comparison</h3>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-200 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="pb-2 pr-4">Signal</th>
                <th className="pb-2 pr-4 text-center">Score Contrib.</th>
                <th className="pb-2 pr-4 text-center">Facts</th>
                <th className="pb-2 pr-4 text-center">SAFE</th>
                <th className="pb-2 pr-4 text-center">Avg Conf</th>
                <th className="pb-2 pr-4 text-center">Domains</th>
                <th className="pb-2 pr-4">Top Entity</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {signalStats.map(stat => (
                <tr key={stat.signal}
                  className={`border-b border-gray-50 last:border-0 cursor-pointer hover:bg-blue-50/30 transition-colors ${selectedSignal === stat.signal ? 'bg-blue-50/50' : ''}`}
                  onClick={() => setSelectedSignal(selectedSignal === stat.signal ? 'all' : stat.signal)}
                >
                  <td className="py-3 pr-4 font-bold text-gray-900">
                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${SIGNAL_COLORS[stat.signal]}`} />
                      {SIGNAL_LABELS[stat.signal]}
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-center font-medium text-indigo-700">
                    {stat.scoreContribution !== null ? stat.scoreContribution.toFixed(1) : '—'}
                  </td>
                  <td className="py-3 pr-4 text-center font-medium tabular-nums text-gray-800">{stat.sFacts.length}</td>
                  <td className="py-3 pr-4 text-center font-medium tabular-nums text-emerald-700">{stat.safeCount}</td>
                  <td className="py-3 pr-4 text-center tabular-nums text-gray-700">
                    {stat.avgConf !== null ? `${(stat.avgConf * 100).toFixed(0)}%` : '—'}
                  </td>
                  <td className="py-3 pr-4 text-center tabular-nums text-gray-700">{stat.domains}</td>
                  <td className="py-3 pr-4 font-medium text-gray-700">{stat.topEntity ?? '—'}</td>
                  <td className="py-3">
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); setSelectedSignal(selectedSignal === stat.signal ? 'all' : stat.signal) }}
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
              · {selectedSignal === 'all' ? 'All Signals' : SIGNAL_LABELS[selectedSignal]}
            </span>
            {evidenceFacts.total > 0 && (
              <span className="text-xs text-gray-400">
                · Showing {evidenceFacts.preview.length} of {evidenceFacts.total} facts
              </span>
            )}
          </div>
          {selectedSignal !== 'all' && (
            <button onClick={() => setSelectedSignal('all')}
              className="ml-2 shrink-0 rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
              Clear filter ×
            </button>
          )}
        </div>

        {evidenceFacts.preview.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-sm text-gray-500">
              {selectedSignal !== 'all'
                ? `No evidence facts for this signal in the latest report.`
                : 'No evidence facts loaded yet.'}
            </p>
          </div>
        ) : (
          <>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {evidenceFacts.preview.map(fact => <EvidenceCard key={fact.fact_id} fact={fact} />)}
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

    </section>
  )
}
