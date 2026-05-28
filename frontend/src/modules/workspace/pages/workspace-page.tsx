import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import WorkspaceNav from '../components/workspace-nav'
import WorkspaceLayout from '../layouts/workspace-layout'
import { CompaniesTab, SignalsTab, EvidenceTab } from '@/modules/dashboard/components/tabs'
import { useDashboardStore } from '@/store/dashboard-store'
import { fetchLatestReportId, fetchReport, fetchReportFacts } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import PricingPage from './pricing-page'
import PipelineAuditPage from './pipeline-audit-page'
import WorkspaceOverview from './workspace-overview'
import type { FactObject, MarketPulseReport, PulseStatus, SignalType } from '@/types/api'

export type WorkspaceView = 'overview' | 'evidence' | 'pricing' | 'signals' | 'companies' | 'pipeline'

interface WorkspacePageProps {
  view: WorkspaceView
}

const VIEW_TO_TAB: Partial<Record<WorkspaceView, 'overview' | 'evidence' | 'signals' | 'companies'>> = {
  overview: 'overview',
  evidence: 'evidence',
  signals: 'signals',
  companies: 'companies',
}

const PULSE_STATUS_LABELS: Record<PulseStatus, string> = {
  heating_up: 'Heating Up',
  stable: 'Stable',
  cooling_down: 'Cooling Down',
  volatile: 'Volatile',
  risk_rising: 'Risk Rising',
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

function strongestSignalFromFacts(facts: FactObject[]): { signal: SignalType; count: number } | null {
  const counts = facts.reduce((acc, fact) => {
    acc[fact.signal_type] = (acc[fact.signal_type] ?? 0) + 1
    return acc
  }, {} as Partial<Record<SignalType, number>>)

  return Object.entries(counts).reduce<{ signal: SignalType; count: number } | null>((best, [signal, count]) => {
    const typedSignal = signal as SignalType
    const typedCount = count ?? 0
    if (!best || typedCount > best.count) return { signal: typedSignal, count: typedCount }
    return best
  }, null)
}

function LoadingView({ message }: { message: string }) {
  return (
    <WorkspaceLayout>
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center">
        <p className="text-sm text-gray-400 animate-pulse">{message}</p>
      </div>
    </WorkspaceLayout>
  )
}

function NoReportView({ error }: { error: string | null }) {
  return (
    <WorkspaceLayout>
      <div className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center gap-6 px-6">
        <div className="max-w-md text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Intelligence Workspace</p>
          <h1 className="mt-2 text-2xl font-bold text-gray-950">No report is available yet</h1>
          <p className="mt-3 text-sm leading-relaxed text-gray-500">
            The workspace reads the latest MarketPulseReport from the FastAPI backend. Refresh after a report is available.
          </p>
          {error && (
            <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
              {error}
            </p>
          )}
        </div>
      </div>
    </WorkspaceLayout>
  )
}

function WorkspaceContent({
  view,
  report,
  facts,
  factsLoading,
}: WorkspacePageProps & {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
}) {
  if (view === 'pricing') return <PricingPage report={report} />
  if (view === 'pipeline') return <PipelineAuditPage />
  if (view === 'evidence') return <EvidenceTab report={report} />
  if (view === 'signals') return <SignalsTab report={report} />
  if (view === 'companies') return <CompaniesTab report={report} />
  return <WorkspaceOverview report={report} facts={facts} factsLoading={factsLoading} />
}

export default function WorkspacePage({ view }: WorkspacePageProps) {
  const { setReport, setActiveTab } = useDashboardStore()

  const { data: latestMeta, isLoading: isResolvingLatest } = useQuery({
    queryKey: ['latestReportId'],
    queryFn: fetchLatestReportId,
    retry: false,
  })

  const latestReportId = latestMeta?.report_id ?? null

  useEffect(() => {
    if (latestMeta?.report_id) {
      localStorage.setItem('pulselens_report_id', latestMeta.report_id)
    }
  }, [latestMeta])

  const {
    data: report,
    isLoading: isLoadingReport,
    error,
    refetch,
  } = useQuery({
    queryKey: ['workspaceReport', latestReportId],
    queryFn: () => fetchReport(latestReportId!),
    enabled: !!latestReportId,
    staleTime: 5 * 60 * 1000,
  })

  const {
    data: facts = [],
    isLoading: isLoadingFacts,
  } = useQuery({
    queryKey: ['workspaceFacts', latestReportId],
    queryFn: () => fetchReportFacts(latestReportId!),
    enabled: !!latestReportId,
    staleTime: 10 * 60 * 1000,
  })

  useEffect(() => {
    if (report) setReport(report)
  }, [report, setReport])

  useEffect(() => {
    const tab = VIEW_TO_TAB[view]
    if (tab) setActiveTab(tab)
  }, [setActiveTab, view])

  if (isResolvingLatest) return <LoadingView message="Checking for latest report…" />
  if (!latestReportId) return <NoReportView error={null} />
  if (isLoadingReport) return <LoadingView message="Loading workspace report…" />

  if (error || !report) {
    const errorMessage = error instanceof Error && error.message.includes('404')
      ? 'Latest report not found. Please refresh or rerun pipeline.'
      : (error as Error | null)?.message ?? 'Failed to load report'

    return (
      <WorkspaceLayout>
        <div className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center gap-4">
          <p className="text-sm text-red-600">{errorMessage}</p>
          <button
            onClick={() => void refetch()}
            className="rounded-lg border border-blue-300 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50"
          >
            Retry
          </button>
        </div>
      </WorkspaceLayout>
    )
  }

  const strongestSignal = strongestSignalFromFacts(facts)
  const pulseStatusLabel = PULSE_STATUS_LABELS[report.pulse_status] ?? report.pulse_status

  return (
    <WorkspaceLayout>
      <main className="mx-auto flex max-w-7xl flex-col gap-7 px-6 py-8">
        <section className="rounded-3xl border border-gray-200 bg-white p-7 shadow-sm">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Intelligence Workspace</p>
              <h1 className="mt-2 text-4xl font-bold tracking-tight text-gray-950">{report.market}</h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-gray-600">
                Analyst workspace for evidence, signals, company lenses, pricing pressure, and pipeline transparency.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                to="/workspace/evidence"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Open Evidence
              </Link>
              <Link
                to="/workspace/pricing"
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Review Pricing
              </Link>
              <Link
                to="/chat"
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Ask Chat
              </Link>
            </div>
          </div>

          <div className="mt-7 grid grid-cols-2 gap-3 text-sm md:grid-cols-3 xl:grid-cols-6">
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Market Status</p>
              <p className="mt-2 text-lg font-bold text-gray-950">{pulseStatusLabel}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Pulse Score</p>
              <p className="mt-2 text-lg font-bold text-gray-950">{report.pulse_score.toFixed(1)}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Quality</p>
              <p className="mt-2 text-lg font-bold text-gray-950">{report.quality_status}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Evidence</p>
              <p className="mt-2 text-lg font-bold text-gray-950">{report.evidence_count}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Sources</p>
              <p className="mt-2 text-lg font-bold text-gray-950">{report.source_count}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Strongest Signal</p>
              <p className="mt-2 text-lg font-bold text-gray-950">
                {isLoadingFacts
                  ? 'Loading'
                  : strongestSignal
                  ? `${SIGNAL_LABELS[strongestSignal.signal]} (${strongestSignal.count})`
                  : 'Unavailable'}
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-5">
            <div className="text-sm text-gray-500">
              Generated {formatDate(report.generated_at)} · Report <span className="font-mono">{report.report_id}</span>
            </div>
            {report.quality_reasons.length > 0 && (
              <div className="max-w-3xl text-sm text-amber-700">
                {report.quality_reasons.slice(0, 2).join('; ')}
              </div>
            )}
          </div>

          <div className="mt-6">
            <WorkspaceNav />
          </div>
        </section>

        <WorkspaceContent view={view} report={report} facts={facts} factsLoading={isLoadingFacts} />
      </main>
    </WorkspaceLayout>
  )
}
