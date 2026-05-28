import { Link } from 'react-router-dom'
import type {
  ContradictionFlag,
  FactObject,
  MarketPulseReport,
  SignalType,
  WatchItem,
} from '@/types/api'
import { normalizeScore } from '@/lib/utils'
import FactIdChip from '@/shared/components/fact-id-chip'

interface WorkspaceOverviewProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading?: boolean
}

const SIGNAL_LABELS: Record<SignalType, string> = {
  hiring_momentum: 'Hiring Momentum',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  strategic_messaging: 'Strategic Messaging',
  investor_signal: 'Investor Signal',
  news_sentiment: 'News Sentiment',
  supplier_risk: 'Supplier Risk',
}

const URGENCY_LABELS: Record<WatchItem['urgency'], { label: string; cls: string }> = {
  this_week: { label: 'This Week', cls: 'bg-red-50 text-red-700 border-red-200' },
  next_2_weeks: { label: 'Next 2 Weeks', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  this_month: { label: 'This Month', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
}

function stripCitationIds(text: string): string {
  return text.replace(/\[(?:fact|claim)_[^\]]+\]/gi, '').replace(/\s{2,}/g, ' ').trim()
}

function signalFactCounts(facts: FactObject[]): Partial<Record<SignalType, number>> {
  return facts.reduce((acc, fact) => {
    acc[fact.signal_type] = (acc[fact.signal_type] ?? 0) + 1
    return acc
  }, {} as Partial<Record<SignalType, number>>)
}

function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function ExecutiveBrief({ report }: { report: MarketPulseReport }) {
  const narrative = report.market_narrative
  const bullets = [
    ...(report.grounded_brief?.what_we_found ?? []).map((statement) => statement.text),
    ...report.top_signals.slice(0, 2).map((signal) => signal.narrative),
    ...report.company_narratives.slice(0, 2).flatMap((company) => company.key_drivers.slice(0, 1)),
  ]
    .map(stripCitationIds)
    .filter(Boolean)
    .slice(0, 4)

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Executive Brief</p>
          <h2 className="mt-2 text-2xl font-bold leading-tight text-gray-950">
            {stripCitationIds(narrative.narrative_headline)}
          </h2>
          <p className="mt-4 text-base leading-7 text-gray-700">
            {stripCitationIds(narrative.narrative_body)}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link
            to="/workspace/evidence"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Open Evidence
          </Link>
          <Link
            to="/chat?context=report"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            Ask Chat
          </Link>
        </div>
      </div>

      {bullets.length > 0 && (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {bullets.map((bullet, index) => (
            <div key={`${bullet}-${index}`} className="rounded-xl bg-gray-50 p-4">
              <p className="text-sm leading-6 text-gray-700">{bullet}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function ActionQueue({ items }: { items: WatchItem[] }) {
  if (!items.length) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Action Queue</p>
        <h2 className="mt-2 text-xl font-bold text-gray-950">No watch items in this report</h2>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          The narrative synthesizer did not surface unresolved forward indicators for this run.
        </p>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Action Queue</p>
          <h2 className="mt-2 text-2xl font-bold text-gray-950">What analysts should monitor next</h2>
        </div>
        <Link to="/workspace/evidence" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          Review supporting evidence
        </Link>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        {items.map((item, index) => {
          const urgency = URGENCY_LABELS[item.urgency] ?? URGENCY_LABELS.this_month
          return (
            <article key={`${item.title}-${index}`} className="rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-base font-bold leading-snug text-gray-950">{item.title}</h3>
                <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${urgency.cls}`}>
                  {urgency.label}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-gray-600">{stripCitationIds(item.rationale)}</p>
              <div className="mt-4 rounded-lg bg-gray-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Trigger</p>
                <p className="mt-1 text-sm leading-5 text-gray-700">{stripCitationIds(item.trigger)}</p>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                <span>{item.signals_pointing_there.length} related evidence refs</span>
                <Link to="/workspace/evidence" className="font-semibold text-blue-600 hover:text-blue-700">
                  Open Evidence
                </Link>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

function RiskAlerts({ contradictions }: { contradictions: ContradictionFlag[] }) {
  if (!contradictions.length) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Risk Alerts</p>
        <h2 className="mt-2 text-xl font-bold text-gray-950">No contradictions surfaced</h2>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          This report did not flag conflicting positive and negative evidence for the same entity and signal.
        </p>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50/40 p-7 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Risk Alerts</p>
      <h2 className="mt-2 text-2xl font-bold text-gray-950">Contradiction review required</h2>
      <div className="mt-5 grid gap-4">
        {contradictions.map((contradiction, index) => (
          <article key={`${contradiction.entity}-${contradiction.signal_type}-${index}`} className="rounded-xl border border-amber-200 bg-white p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-800">
                {contradiction.entity}
              </span>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                {SIGNAL_LABELS[contradiction.signal_type] ?? contradiction.signal_type}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-gray-700">{stripCitationIds(contradiction.note)}</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="rounded-lg bg-emerald-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Supporting evidence</p>
                <p className="mt-1 text-sm text-emerald-900">{contradiction.positive_facts.length} fact refs</p>
                <div className="mt-2 flex flex-wrap gap-1.5 opacity-80">
                  {contradiction.positive_facts.slice(0, 4).map((factId) => (
                    <FactIdChip key={factId} factId={factId} />
                  ))}
                </div>
              </div>
              <div className="rounded-lg bg-red-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Against evidence</p>
                <p className="mt-1 text-sm text-red-900">{contradiction.negative_facts.length} fact refs</p>
                <div className="mt-2 flex flex-wrap gap-1.5 opacity-80">
                  {contradiction.negative_facts.slice(0, 4).map((factId) => (
                    <FactIdChip key={factId} factId={factId} />
                  ))}
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm font-semibold text-amber-800">Recommended action: Review evidence before acting.</p>
          </article>
        ))}
      </div>
    </section>
  )
}

function SignalCockpit({
  report,
  facts,
  factsLoading,
}: {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading?: boolean
}) {
  const counts = signalFactCounts(facts)

  if (!report.top_signals.length) return null

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Signal Cockpit</p>
          <h2 className="mt-2 text-2xl font-bold text-gray-950">Score contribution and evidence depth</h2>
        </div>
        <Link to="/workspace/signals" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          Open signal radar
        </Link>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {report.top_signals.map((signal) => {
          const normalized = normalizeScore(signal.score)
          const evidenceCount = counts[signal.signal_type]
          return (
            <Link
              key={signal.signal_type}
              to="/workspace/signals"
              className="rounded-xl border border-gray-200 p-5 transition-colors hover:border-blue-300 hover:bg-blue-50/30"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-gray-950">
                    {SIGNAL_LABELS[signal.signal_type] ?? signal.signal_type}
                  </h3>
                  <p className="mt-1 text-sm leading-5 text-gray-500">{stripCitationIds(signal.narrative)}</p>
                </div>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
                  {normalized}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
                  <div className="h-full rounded-full bg-blue-500" style={{ width: `${normalized}%` }} />
                </div>
                <span className="w-24 text-right text-xs text-gray-500">
                  {factsLoading ? 'facts loading' : `${evidenceCount ?? 0} facts`}
                </span>
              </div>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

function StockCoveragePanel({ report }: { report: MarketPulseReport }) {
  const rows = report.company_narratives.filter(
    (company) =>
      company.price_current != null ||
      company.price_change_7d_pct != null ||
      company.signal_lead_days != null,
  )

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Market Data Context</p>
          <h2 className="mt-2 text-2xl font-bold text-gray-950">Price context</h2>
        </div>
        <Link to="/workspace/companies" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          Open company lens
        </Link>
      </div>

      {rows.length === 0 ? (
        <div className="mt-5 rounded-xl bg-gray-50 p-5">
          <p className="text-sm leading-6 text-gray-600">
            Market data coverage is limited for this report. PulseLens is showing evidence-backed signal context
            without fabricating price rows.
          </p>
        </div>
      ) : (
        <div className="mt-5 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-2 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Company</th>
                <th className="pb-2 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Price</th>
                <th className="pb-2 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">7d change</th>
                <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Signal lead</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((company) => (
                <tr key={company.ticker} className="border-b border-gray-100 last:border-0">
                  <td className="py-3 pr-4 text-sm font-semibold text-gray-900">{company.company} ({company.ticker})</td>
                  <td className="py-3 pr-4 text-sm tabular-nums text-gray-700">
                    {company.price_current != null ? `$${company.price_current.toFixed(2)}` : 'Unavailable'}
                  </td>
                  <td className="py-3 pr-4 text-sm tabular-nums text-gray-700">
                    {company.price_change_7d_pct != null ? `${company.price_change_7d_pct >= 0 ? '+' : ''}${company.price_change_7d_pct.toFixed(1)}%` : 'Unavailable'}
                  </td>
                  <td className="py-3 text-sm text-gray-700">
                    {company.signal_lead_days != null ? `${company.signal_lead_days} days` : 'Unavailable'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function EvidencePreview({ facts }: { facts: FactObject[] }) {
  const topFacts = [...facts].sort((a, b) => b.confidence - a.confidence).slice(0, 3)

  if (!topFacts.length) return null

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Evidence Preview</p>
          <h2 className="mt-2 text-2xl font-bold text-gray-950">Highest-confidence facts</h2>
        </div>
        <Link to="/workspace/evidence" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          Open Evidence
        </Link>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        {topFacts.map((fact) => (
          <article key={fact.fact_id} className="rounded-xl border border-gray-200 p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {SIGNAL_LABELS[fact.signal_type]}
              </span>
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
                T{fact.source_tier}
              </span>
            </div>
            <h3 className="mt-4 text-sm font-bold leading-6 text-gray-950">{fact.claim}</h3>
            <p className="mt-3 border-l-2 border-blue-200 pl-3 text-sm leading-6 text-gray-600">
              "{fact.evidence_quote}"
            </p>
            <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
              <span>{fact.entity}</span>
              <span>{sourceDomain(fact.source_url)} · {(fact.confidence * 100).toFixed(0)}%</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default function WorkspaceOverview({ report, facts, factsLoading = false }: WorkspaceOverviewProps) {
  return (
    <div className="flex flex-col gap-6">
      <ExecutiveBrief report={report} />
      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <ActionQueue items={report.market_narrative.watch_list ?? []} />
        <RiskAlerts contradictions={report.contradictions ?? []} />
      </div>
      <SignalCockpit report={report} facts={facts} factsLoading={factsLoading} />
      <EvidencePreview facts={facts} />
      <StockCoveragePanel report={report} />
    </div>
  )
}
