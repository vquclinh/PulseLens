// Screen 2 — full intelligence dashboard: topbar + tabs + collapsible chat panel
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Topbar from '../components/topbar'
import TabNav from '../components/tab-nav'
import { OverviewTab, CompaniesTab, SignalsTab, NewsTab, EvidenceTab } from '../components/tabs'
import ChatPanel from '@/modules/chat/components/chat-panel'
import { useDashboardStore } from '@/store/dashboard-store'
import { fetchReport, fetchLatestReportId, runPipeline } from '@/lib/api-client'

// ── View states ───────────────────────────────────────────────────────────────

function LoadingView({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-sm text-gray-400 animate-pulse">{message}</p>
    </div>
  )
}

function RunningView() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      <p className="text-sm font-medium text-gray-600">Running pipeline — collecting signals…</p>
      <p className="text-xs text-gray-400">This takes 5–10 minutes. Please wait.</p>
    </div>
  )
}

function NoReportView({
  market,
  onRun,
  isRunning,
  error,
}: {
  market: string | undefined
  onRun: () => void
  isRunning: boolean
  error: string | null
}) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-6 px-6">
      <div className="text-center max-w-md">
        <div className="text-4xl mb-4">📡</div>
        <h1 className="text-xl font-bold text-gray-900 mb-2">No analysis yet</h1>
        <p className="text-sm text-gray-500 mb-6">
          Generate a fresh market intelligence report for{' '}
          <strong className="text-gray-700">{market?.replace(/-/g, ' ') ?? 'US AI Hardware'}</strong>.
          This runs the full 8-company pipeline (takes 5–10 minutes).
        </p>
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 mb-4">
            {error}
          </p>
        )}
        <button
          onClick={onRun}
          disabled={isRunning}
          className="px-6 py-3 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
        >
          {isRunning ? 'Running analysis…' : 'Generate Analysis'}
        </button>
      </div>
    </div>
  )
}

function ErrorView({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <p className="text-sm text-red-600">{error?.message ?? 'Failed to load report'}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50"
      >
        Retry
      </button>
    </div>
  )
}

// ── Dashboard page ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { market } = useParams<{ market: string }>()
  const { activeTab, isChatOpen, setReport } = useDashboardStore()

  const [reportId, setReportId] = useState<string | null>(
    () => localStorage.getItem('pulselens_report_id'),
  )
  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  // When localStorage is empty, ask the backend for the most recent pipeline report.
  // This makes the legacy dashboard route auto-load existing data without triggering a new run.
  const { data: latestMeta, isLoading: isResolvingLatest } = useQuery({
    queryKey: ['latest-report-id'],
    queryFn: fetchLatestReportId,
    enabled: !reportId,
    retry: false,   // 404 = no reports exist yet — show NoReportView immediately
  })

  useEffect(() => {
    if (latestMeta?.report_id && !reportId) {
      localStorage.setItem('pulselens_report_id', latestMeta.report_id)
      setReportId(latestMeta.report_id)
    }
  }, [latestMeta, reportId])

  const {
    data: report,
    isLoading: isLoadingReport,
    error,
  } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (report) setReport(report)
  }, [report, setReport])

  async function handleRunPipeline() {
    setIsRunning(true)
    setRunError(null)
    try {
      const res = await runPipeline({
        market: market?.replace(/-/g, ' ') ?? 'AI Hardware Semiconductor',
      })
      localStorage.setItem('pulselens_report_id', res.report_id)
      setReportId(res.report_id)
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'Pipeline run failed')
    } finally {
      setIsRunning(false)
    }
  }

  if (isRunning) return <RunningView />

  // Resolving the latest report from backend (only when localStorage was empty)
  if (!reportId && isResolvingLatest) {
    return <LoadingView message="Checking for existing reports…" />
  }

  // Truly nothing exists — ask user to run the pipeline for the first time
  if (!reportId) {
    return (
      <NoReportView
        market={market}
        onRun={handleRunPipeline}
        isRunning={isRunning}
        error={runError}
      />
    )
  }

  if (isLoadingReport) return <LoadingView message="Loading report…" />
  if (error || !report) return <ErrorView error={error as Error} onRetry={handleRunPipeline} />

  return (
    <div className="min-h-screen bg-gray-50">
      <Topbar report={report} onRefresh={handleRunPipeline} isRefreshing={isRunning} />
      <TabNav report={report} />

      <main
        className="max-w-7xl mx-auto px-6 py-6 transition-all duration-300"
        style={{ marginRight: isChatOpen ? '384px' : undefined }}
      >
        {activeTab === 'overview'  && <OverviewTab  report={report} />}
        {activeTab === 'companies' && <CompaniesTab report={report} />}
        {activeTab === 'signals'   && <SignalsTab   report={report} />}
        {activeTab === 'news'      && <NewsTab      report={report} />}
        {activeTab === 'evidence'  && <EvidenceTab  report={report} />}
      </main>

      {isChatOpen && <ChatPanel reportId={reportId} />}
    </div>
  )
}
