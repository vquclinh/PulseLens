import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { FactObject, MarketPulseReport } from '@/types/api'
import { formatDate } from '@/lib/utils'
import {
  ShieldCheck, AlertTriangle, ArrowRight, Database, Code, Shield, CheckCircle, Network, BookOpen, Clock, Activity, FileText
} from 'lucide-react'

interface PipelineAuditPageProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
  factsError: Error | null
}

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

const PIPELINE_STAGES = [
  {
    icon: <Database className="h-5 w-5 text-blue-600" />,
    title: '1. Query planning',
    desc: 'The pipeline decomposes the market tracking goal into specific company and sector queries using LLM reasoning to ensure broad coverage.',
  },
  {
    icon: <Network className="h-5 w-5 text-indigo-600" />,
    title: '2. Web collection',
    desc: 'Live scraping of news, investor relations, job boards, and pricing pages via SERP APIs. Each raw document is assigned a source tier (1-4).',
  },
  {
    icon: <FileText className="h-5 w-5 text-amber-600" />,
    title: '3. Fact extraction',
    desc: 'Schema-constrained extraction identifies discrete claims. Every fact must extract an exact, verbatim evidence quote from the source document text.',
  },
  {
    icon: <ShieldCheck className="h-5 w-5 text-emerald-600" />,
    title: '4. SAFE verification',
    desc: 'Search-Augmented Fact Evaluation checks each extracted claim against the broader web. Claims failing verification are flagged and discarded or downgraded.',
  },
  {
    icon: <Activity className="h-5 w-5 text-purple-600" />,
    title: '5. Signal scoring',
    desc: 'Verified facts are mapped to predefined signal types (e.g. pricing pressure, product launch). Scores are calculated based on tier, confidence, and recency.',
  },
  {
    icon: <BookOpen className="h-5 w-5 text-teal-600" />,
    title: '6. Narrative synthesis',
    desc: 'The backend orchestrates market-level and company-level summaries, pulling only from the pool of validated signal data to avoid hallucination.',
  },
  {
    icon: <CheckCircle className="h-5 w-5 text-green-600" />,
    title: '7. Report assembly',
    desc: 'All data is assembled into the unified MarketPulseReport format, computing the final Pulse Score, momentum scores, and determining the Quality PASS status.',
  },
  {
    icon: <Code className="h-5 w-5 text-slate-600" />,
    title: '8. Database persistence',
    desc: 'The final report and all evidence facts are written to Supabase/Postgres. The frontend queries this data directly via FastAPI without triggering new pipeline runs.',
  },
]

export default function PipelineAuditPage({ report, facts = [], factsLoading, factsError }: PipelineAuditPageProps) {
  const safeCount = useMemo(() => facts.filter(f => f.safe_verified).length, [facts])
  const domainSetSize = useMemo(() => new Set(facts.map(f => sourceDomain(f.source_url))).size, [facts])
  
  const sourceTiers = useMemo(() => {
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0 }
    facts.forEach(f => {
      if (f.source_tier in counts) counts[f.source_tier as 1|2|3|4]++
    })
    return counts
  }, [facts])

  const topDomains = useMemo(() => {
    const counts: Record<string, number> = {}
    facts.forEach(f => {
      const d = sourceDomain(f.source_url)
      counts[d] = (counts[d] ?? 0) + 1
    })
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5)
  }, [facts])

  const avgConf = useMemo(() => 
    facts.length > 0 ? facts.reduce((acc, f) => acc + f.confidence, 0) / facts.length : null
  , [facts])

  const audit = report.audit_summary

  if (factsLoading) {
    return (
      <div className="flex animate-pulse flex-col gap-6">
        <div className="h-32 rounded-2xl bg-white border border-gray-200" />
        <div className="h-64 rounded-2xl bg-white border border-gray-200" />
      </div>
    )
  }

  if (factsError) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-500" />
        <h3 className="mt-3 text-base font-bold text-red-950">Audit data load failed</h3>
        <p className="mt-2 text-sm text-red-700">{factsError.message}</p>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-6 pb-12" id="trust-pipeline-workspace">
      
      {/* Header */}
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-blue-600">
              <Shield className="h-4 w-4" /> Trust & Pipeline
            </p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-gray-950">Trust & Pipeline</h2>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-gray-600">
              How PulseLens collects, verifies, scores, and stores market intelligence.
            </p>
          </div>
          <span className="shrink-0 font-mono text-xs text-gray-400">
            Report: <span className="font-semibold text-gray-600">{report.report_id}</span>
          </span>
        </div>
      </div>

      {/* Live Quality Summary */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Quality Status</p>
          <p className={`mt-1 text-lg font-bold ${report.quality_status === 'PASS' ? 'text-emerald-600' : 'text-amber-600'}`}>
            {report.quality_status}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Evidence Facts</p>
          <p className="mt-1 text-lg font-bold text-gray-900">{facts.length}</p>
        </div>
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">SAFE Verified</p>
          <p className="mt-1 text-lg font-bold text-emerald-700">{safeCount}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Source Domains</p>
          <p className="mt-1 text-lg font-bold text-gray-900">{domainSetSize}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Pulse Score</p>
          <p className="mt-1 text-lg font-bold text-blue-600">{report.pulse_score.toFixed(1)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Generated</p>
          <p className="mt-1 text-sm font-bold text-gray-700 mt-2">{formatDate(report.generated_at)}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Source Quality (2/3 width) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm flex-1">
            <h3 className="flex items-center gap-2 text-base font-bold text-gray-900">
              <Network className="h-5 w-5 text-indigo-500" /> Source Quality Breakdown
            </h3>
            <p className="mt-2 text-sm text-gray-600 leading-relaxed">
              Live distribution of evidence facts across source tiers. Tier 1 (official docs, SEC, IR) and Tier 2 (major news) carry the highest scoring weight.
            </p>
            
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[1, 2, 3, 4].map(tier => {
                const count = sourceTiers[tier as 1|2|3|4]
                const pct = facts.length > 0 ? Math.round((count / facts.length) * 100) : 0
                return (
                  <div key={tier} className="flex flex-col items-center justify-center rounded-xl bg-slate-50 p-4 border border-slate-100">
                    <span className="text-xs font-bold uppercase text-slate-500">Tier {tier}</span>
                    <span className="mt-1 text-2xl font-black text-slate-800">{count}</span>
                    <span className="mt-1 text-[10px] text-slate-400">{pct}% of facts</span>
                  </div>
                )
              })}
            </div>

            <div className="mt-6 pt-5 border-t border-gray-100 flex flex-wrap gap-x-8 gap-y-4">
              <div>
                <p className="text-xs font-semibold text-gray-500">Top Domains Found</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {topDomains.map(([domain, count]) => (
                    <span key={domain} className="rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-700 font-medium border border-gray-200">
                      {domain} <span className="ml-1 text-[10px] text-gray-400">({count})</span>
                    </span>
                  ))}
                </div>
              </div>
              <div className="ml-auto flex gap-6">
                <div>
                  <p className="text-xs font-semibold text-gray-500">Average Fact Confidence</p>
                  <p className="mt-1 text-lg font-bold text-gray-900">
                    {avgConf !== null ? `${(avgConf * 100).toFixed(1)}%` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-emerald-600">SAFE Ratio</p>
                  <p className="mt-1 text-lg font-bold text-emerald-700">
                    {facts.length > 0 ? `${Math.round((safeCount / facts.length) * 100)}%` : '—'}
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Quality Gate */}
          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="flex items-center gap-2 text-base font-bold text-gray-900">
              <CheckCircle className="h-5 w-5 text-emerald-500" /> Pipeline Quality Gate
            </h3>
            {audit ? (
              <div className="mt-4 text-sm">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="rounded-lg bg-gray-50 p-3 border border-gray-100">
                    <span className="block text-[10px] uppercase text-gray-500 font-semibold">Queries Run</span>
                    <span className="text-lg font-bold text-gray-900">{audit.query_count ?? '—'}</span>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3 border border-gray-100">
                    <span className="block text-[10px] uppercase text-gray-500 font-semibold">Accepted Docs</span>
                    <span className="text-lg font-bold text-gray-900">{audit.accepted_doc_count ?? '—'}</span>
                  </div>
                </div>
                
                {report.quality_reasons.length > 0 && (
                  <div className="mt-4 rounded-lg bg-amber-50 p-3 border border-amber-100">
                    <span className="block text-[10px] uppercase text-amber-600 font-semibold mb-1">Quality Reasons / Warnings</span>
                    <ul className="list-disc pl-4 text-xs text-amber-800 space-y-1">
                      {report.quality_reasons.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {audit.missing_signal_types && audit.missing_signal_types.length > 0 && (
                  <div className="mt-3">
                    <span className="block text-[10px] uppercase text-gray-500 font-semibold mb-1">Missing Signal Coverage</span>
                    <div className="flex flex-wrap gap-1.5">
                      {audit.missing_signal_types.map(sig => (
                        <span key={sig} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">{sig}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="mt-4 text-sm text-gray-500 italic bg-gray-50 p-4 rounded-lg border border-gray-100">
                Detailed audit artifacts are not exposed through the current frontend API payload for this report. This page displays live report/fact-derived quality indicators and process transparency.
              </p>
            )}
          </section>
        </div>

        {/* Data Provenance & Trust */}
        <div className="flex flex-col gap-6">
          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="flex items-center gap-2 text-base font-bold text-gray-900">
              <Database className="h-5 w-5 text-blue-500" /> Data Provenance
            </h3>
            <p className="mt-3 text-sm text-gray-600 leading-relaxed">
              All workspace pages read exclusively from the live <strong>FastAPI backend</strong> via standard API requests. 
            </p>
            <div className="mt-4 flex flex-col gap-2 font-mono text-[10px] text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div className="flex items-center gap-2"><ArrowRight className="h-3 w-3 text-blue-400" /> GET /api/reports/latest</div>
              <div className="flex items-center gap-2"><ArrowRight className="h-3 w-3 text-blue-400" /> GET /api/report/{'{id}'}</div>
              <div className="flex items-center gap-2"><ArrowRight className="h-3 w-3 text-blue-400" /> GET /api/report/{'{id}'}/facts</div>
            </div>
            <p className="mt-4 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-4">
              When the backend runs with <code className="text-xs bg-gray-100 px-1 rounded text-pink-600">DATABASE_BACKEND=postgres</code>, all reports and facts are persisted safely in <strong>Supabase/Postgres</strong>. The frontend does not execute direct Supabase client calls.
            </p>
            <div className="mt-4 bg-blue-50 border border-blue-100 rounded-lg p-3">
              <p className="text-xs text-blue-800 font-medium flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" /> No mock fallback data
              </p>
              <p className="mt-1 text-[11px] text-blue-700 leading-relaxed">
                If the backend is unavailable, workspace tabs will render hard error states. Demo fallback data is strictly confined to the Home page marketing view and is never mixed with live intelligence.
              </p>
            </div>
          </section>
        </div>
      </div>

      {/* Pipeline Stages */}
      <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <h3 className="flex items-center gap-2 text-lg font-bold text-gray-900 mb-6">
          <Clock className="h-5 w-5 text-slate-500" /> The PulseLens Pipeline
        </h3>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 relative">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={i} className="relative z-10 flex flex-col gap-2 rounded-xl bg-slate-50 border border-slate-100 p-5 shadow-sm hover:border-blue-200 transition-colors">
              <div className="flex items-center gap-2 mb-1">
                {stage.icon}
                <h4 className="font-bold text-sm text-gray-900">{stage.title}</h4>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">{stage.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTAs */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Link to="/workspace/evidence"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50/60 to-indigo-50/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Open Evidence Explorer</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">Inspect the verified facts that power this report.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-600">
            View evidence <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
        <Link to="/workspace/signals"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-emerald-50/40 to-teal-50/40 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Review Signal Radar</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">See how evidence translates into market signals.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
            View signals <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
        <Link to="/chat"
          className="rounded-2xl border border-gray-200 bg-gradient-to-br from-slate-50 to-gray-50 p-5 shadow-sm hover:shadow-md transition-shadow">
          <p className="text-sm font-bold text-gray-900">Ask Chat about this report</p>
          <p className="mt-1 text-xs text-gray-600 leading-relaxed">Query the knowledge base using natural language.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-indigo-600">
            Open Chat <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
      </div>

    </section>
  )
}
