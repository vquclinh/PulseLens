import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '@/shared/components/navbar'
import ChatInput from '../components/chat-input'
import ChatMessageBubble from '../components/chat-message'
import { useChat } from '@/hooks/use-chat'
import type { AttachmentSnippet, MessageWithFacts } from '@/hooks/use-chat'
import { fetchLatestReportId, fetchReport, fetchReportFacts } from '@/lib/api-client'
import type { ContextAttachment, MarketPulseReport, FactObject } from '@/types/api'
import { FileText, Building2, Activity, Tag, BarChart2, Eye, AlertTriangle, X } from 'lucide-react'

// Formats report.generated_at as "Report updated May 28, 2026 · 04:05 UTC"
function formatReportTimestamp(ts: string | null | undefined): string {
  if (!ts) return 'Latest report loaded'
  try {
    const d = new Date(ts)
    const date = d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
    })
    const time = d.toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
    })
    return `Report updated ${date} · ${time} UTC`
  } catch {
    return 'Latest report loaded'
  }
}

// ─── Context card (shown for all context types) ───────────────────────────────

function ContextCard({
  contextType,
  searchParams,
  report,
  facts,
  onPromptClick,
  onDismiss,
}: {
  contextType: string
  searchParams: URLSearchParams
  report: MarketPulseReport | undefined
  facts: FactObject[] | undefined
  onPromptClick: (p: string) => void
  onDismiss?: () => void
}) {
  let title = 'Chatting about this context'
  let details = null
  let prompts: string[] = []
  let icon = <FileText className="h-5 w-5 text-blue-600" />
  let isValid = false
  const isDismissible = contextType === 'watch_item' || contextType === 'risk_alert' || contextType === 'fact'

  if (contextType === 'fact') {
    const factId = searchParams.get('fact_id')
    const fact = facts?.find(f => f.fact_id === factId)
    if (fact) {
      isValid = true
      title = 'Chatting about this evidence fact'
      details = (
        <div className="mt-2 text-sm text-gray-600">
          <p className="font-medium text-gray-900 leading-relaxed">"{fact.claim}"</p>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="rounded bg-slate-200/50 px-1.5 py-0.5 text-slate-700">{fact.signal_type.replace('_', ' ')}</span>
            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 font-medium">{(fact.confidence * 100).toFixed(0)}% conf</span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600 truncate max-w-[150px]">
              {new URL(fact.source_url).hostname.replace(/^www\./, '')}
            </span>
          </div>
        </div>
      )
      prompts = ['Explain why this fact matters', 'What other facts support this?', 'Is there contradictory evidence?']
    }
  } else if (contextType === 'company') {
    const company = searchParams.get('company')
    if (company && report) {
      isValid = true
      icon = <Building2 className="h-5 w-5 text-blue-600" />
      title = `Chatting about ${company}`
      const cn = report.company_narratives.find(n => n.company === company || n.ticker === company)
      const count = facts?.filter(f => {
        const e = f.entity.toLowerCase(), c = company.toLowerCase()
        return e === c || c.startsWith(e) || e.startsWith(c) || (cn && e === cn.ticker.toLowerCase())
      }).length ?? 0
      details = (
        <div className="mt-2 text-sm text-gray-600">
          {cn && <span className="font-medium text-gray-900 mr-2">Ticker: {cn.ticker}</span>}
          <span>{count} supporting facts</span>
        </div>
      )
      prompts = [`Summarize ${company}'s current market read`, `Which signals are strongest for ${company}?`, 'What should I watch next?']
    }
  } else if (contextType === 'signal') {
    const signal = searchParams.get('signal')
    if (signal) {
      isValid = true
      icon = <Activity className="h-5 w-5 text-blue-600" />
      title = `Chatting about ${signal.replace(/_/g, ' ')}`
      const count = facts?.filter(f => f.signal_type === signal).length ?? 0
      details = <div className="mt-2 text-sm text-gray-600"><span>{count} supporting facts</span></div>
      prompts = ['Summarize this signal', 'Which companies are involved?', 'Show the strongest supporting facts']
    }
  } else if (contextType === 'pricing') {
    isValid = true
    icon = <Tag className="h-5 w-5 text-blue-600" />
    title = 'Chatting about Pricing Intelligence'
    const count = facts?.filter(f => f.signal_type === 'pricing_pressure').length ?? 0
    details = <div className="mt-2 text-sm text-gray-600"><span>{count} pricing pressure facts</span></div>
    prompts = ['What pricing pressure signals matter most?', 'Which providers appear in pricing evidence?', 'Are any pricing facts weak or noisy?']
  } else if (contextType === 'report') {
    isValid = true
    icon = <BarChart2 className="h-5 w-5 text-blue-600" />
    title = 'Chatting about latest report'
    details = (
      <div className="mt-2 text-sm text-gray-600">
        <p>Report: <span className="font-mono">{report?.report_id}</span></p>
        <div className="mt-1 flex gap-2 text-xs">
          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-blue-700 font-medium">Score: {report?.pulse_score.toFixed(1)}</span>
          {report?.quality_status === 'PASS' && <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 font-medium">PASS</span>}
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">{facts?.length ?? 0} facts</span>
        </div>
      </div>
    )
    prompts = ['Give me the executive summary', 'What are the top risks?', 'What evidence should I inspect first?']
  } else if (contextType === 'watch_item') {
    const titleParam = searchParams.get('title')
    const item = report?.market_narrative.watch_list?.find(i => i.title === titleParam)
    if (item) {
      isValid = true
      icon = <Eye className="h-5 w-5 text-blue-600" />
      title = `Watch item: ${item.title}`
      const urgencyLabel: Record<string, string> = { this_week: 'This Week', next_2_weeks: 'Next 2 Weeks', this_month: 'This Month' }
      details = (
        <div className="mt-2 space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
              {urgencyLabel[item.urgency] ?? item.urgency}
            </span>
            <span className="text-xs text-gray-400">{item.signals_pointing_there.length} signal refs</span>
          </div>
          <p className="text-gray-700 leading-relaxed line-clamp-3">{item.rationale}</p>
          <div className="rounded-lg bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-0.5">Trigger</p>
            <p className="text-xs text-gray-700 line-clamp-2">{item.trigger}</p>
          </div>
        </div>
      )
      prompts = ['Why should we monitor this?', 'What evidence supports this watch item?', 'What could change the market read?']
    }
  } else if (contextType === 'risk_alert') {
    const entityParam = searchParams.get('entity')
    const signalParam = searchParams.get('signal')
    const item = report?.contradictions?.find(c => c.entity === entityParam && c.signal_type === signalParam)
    if (item) {
      isValid = true
      icon = <AlertTriangle className="h-5 w-5 text-amber-600" />
      title = `Risk alert: ${item.entity}`
      details = (
        <div className="mt-2 space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-700">{item.entity}</span>
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">{item.signal_type.replace(/_/g, ' ')}</span>
          </div>
          <p className="text-gray-700 leading-relaxed line-clamp-3">{item.note}</p>
          <div className="flex gap-4 text-xs">
            <span className="font-medium text-emerald-600">{item.positive_facts.length} supporting</span>
            <span className="font-medium text-red-600">{item.negative_facts.length} against</span>
          </div>
        </div>
      )
      prompts = ['Explain this contradiction', 'Which side has stronger evidence?', 'What should an analyst check next?']
    }
  }

  if (!isValid && report && facts) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm text-center">
        <p className="text-sm font-medium text-gray-700">
          Attached context was not found in the latest report. You can still ask about the report.
        </p>
      </div>
    )
  }
  if (!isValid) return null

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 shadow-sm ring-1 ring-blue-50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-sm font-bold text-gray-900">{title}</h3>
        </div>
        {isDismissible && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Remove attached context"
            className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {details}
      <div className="mt-3 flex flex-wrap gap-2">
        {prompts.map(p => (
          <button
            key={p}
            onClick={() => {
              onPromptClick(p)
              setTimeout(() => document.getElementById('chat-input-textarea')?.focus(), 10)
            }}
            className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 transition-colors shadow-sm"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Chat console ─────────────────────────────────────────────────────────────

function ChatConsole({ reportId }: { reportId: string }) {
  const { messages, sendMessage, isPending } = useChat(reportId)
  const [input, setInput] = useState('')
  const [attachmentDismissed, setAttachmentDismissed] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const contextType = searchParams.get('context')
  // fact context is now also treated as an attachment-bar context
  const isOverviewContext = contextType === 'watch_item' || contextType === 'risk_alert' || contextType === 'fact'

  const { data: report } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId),
    staleTime: Infinity,
  })
  const { data: facts } = useQuery({
    queryKey: ['facts', reportId],
    queryFn: () => fetchReportFacts(reportId),
    staleTime: Infinity,
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /** Clear all context URL params and mark attachment as dismissed. */
  function dismissAttachment() {
    setAttachmentDismissed(true)
    setSearchParams({}, { replace: true })
  }

  /** Derive hostname from a URL string safely. */
  function domainOf(url: string): string {
    try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
  }

  /**
   * Build the structured ContextAttachment to send to the backend.
   * Returns undefined when no active attachment exists or it has been dismissed.
   */
  function buildContextAttachment(): ContextAttachment | undefined {
    if (attachmentDismissed || !isOverviewContext || !contextType) return undefined

    if (contextType === 'watch_item') {
      if (!report) return undefined
      const titleParam = searchParams.get('title')
      const item = report.market_narrative.watch_list?.find(i => i.title === titleParam)
      if (!item) return undefined
      return {
        type: 'watch_item',
        title: item.title,
        urgency: item.urgency,
        rationale: item.rationale,
        trigger: item.trigger,
        summary: `Watch item: ${item.title} (${item.urgency})`,
      }
    }

    if (contextType === 'risk_alert') {
      if (!report) return undefined
      const entityParam = searchParams.get('entity')
      const signalParam = searchParams.get('signal')
      const item = report.contradictions?.find(
        c => c.entity === entityParam && c.signal_type === signalParam,
      )
      if (!item) return undefined
      return {
        type: 'risk_alert',
        entity: item.entity,
        signal_type: item.signal_type,
        summary: item.note,
        supporting_count: item.positive_facts.length,
        against_count: item.negative_facts.length,
      }
    }

    if (contextType === 'fact') {
      const factId = searchParams.get('fact_id')
      const fact = facts?.find(f => f.fact_id === factId)
      if (!fact) return undefined
      return {
        type: 'fact',
        title: fact.claim,
        entity: fact.entity,
        signal_type: fact.signal_type,
        summary: fact.evidence_quote,
        evidence_quote: fact.evidence_quote,
        confidence: fact.confidence,
        source_domain: domainOf(fact.source_url),
        source_tier: fact.source_tier,
        fact_id: fact.fact_id,
      }
    }

    return undefined
  }

  /**
   * Build the rich compact snippet stored in the submitted user message bubble.
   * Returns undefined when no active attachment or it has been dismissed.
   */
  function buildAttachmentSnippet(): AttachmentSnippet | undefined {
    if (attachmentDismissed || !isOverviewContext || !contextType) return undefined

    if (contextType === 'watch_item') {
      if (!report) return undefined
      const titleParam = searchParams.get('title')
      const item = report.market_narrative.watch_list?.find(i => i.title === titleParam)
      if (!item) return undefined
      const urgencyLabel: Record<string, string> = {
        this_week: 'This Week', next_2_weeks: 'Next 2 Weeks', this_month: 'This Month',
      }
      return {
        label: 'Watch item',
        title: item.title,
        badgeText: urgencyLabel[item.urgency] ?? item.urgency,
        body: item.rationale,
        body2: item.trigger,
        body2Label: 'Trigger',
      }
    }

    if (contextType === 'risk_alert') {
      if (!report) return undefined
      const entityParam = searchParams.get('entity')
      const signalParam = searchParams.get('signal')
      const item = report.contradictions?.find(
        c => c.entity === entityParam && c.signal_type === signalParam,
      )
      if (!item) return undefined
      return {
        label: 'Risk alert',
        title: item.entity,
        badgeText: item.signal_type.replace(/_/g, ' '),
        body: item.note,
        meta: `${item.positive_facts.length} supporting · ${item.negative_facts.length} against`,
      }
    }

    if (contextType === 'fact') {
      const factId = searchParams.get('fact_id')
      const fact = facts?.find(f => f.fact_id === factId)
      if (!fact) return undefined
      return {
        label: 'Evidence fact',
        title: fact.claim,
        body: `"${fact.evidence_quote}"`,
        meta: `${fact.entity} · ${fact.signal_type.replace(/_/g, ' ')} · ${domainOf(fact.source_url)} · ${(fact.confidence * 100).toFixed(0)}% conf`,
      }
    }

    return undefined
  }

  function handleSubmit() {
    const userText = input.trim()
    if (!userText || isPending) return
    setInput('')

    const contextAttachment = buildContextAttachment()
    const snippet = buildAttachmentSnippet()

    // Send: user text shown in UI, structured attachment to backend
    sendMessage(userText, userText, snippet, contextAttachment)

    // Clear attachment after send — it now lives in the message bubble
    if (isOverviewContext && !attachmentDismissed) {
      dismissAttachment()
    }
  }

  const showAttachmentBar = isOverviewContext && !attachmentDismissed

  return (
    <section className="mx-auto flex h-[calc(100vh-128px)] max-w-5xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 px-6 py-4 flex justify-between items-center bg-white z-10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Analyst Chat</p>
          <h1 className="mt-1 text-2xl font-bold text-gray-950">Ask questions grounded in latest report evidence</h1>
        </div>
        <p className="text-xs text-gray-400">{formatReportTimestamp(report?.generated_at)}</p>
      </div>

      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 bg-slate-50/50">
        {/* Existing context types (non-overview) remain at top of messages */}
        {contextType && !isOverviewContext && (
          <div className="mb-6">
            <ContextCard
              contextType={contextType}
              searchParams={searchParams}
              report={report}
              facts={facts}
              onPromptClick={setInput}
            />
          </div>
        )}

        {messages.length === 0 ? (
          <div className="mx-auto mt-6 max-w-xl text-center">
            {!contextType && (
              <>
                <p className="text-sm text-gray-500">Try asking about supplier risks, pricing pressure, or company momentum.</p>
                <div className="mt-5 grid gap-2 text-left">
                  {[
                    'What are the strongest signals in this report?',
                    'Which company has the most pricing pressure evidence?',
                    'What supplier risks should I monitor next?',
                  ].map((question) => (
                    <button
                      key={question}
                      onClick={() => {
                        setInput(question)
                        setTimeout(() => document.getElementById('chat-input-textarea')?.focus(), 10)
                      }}
                      className="rounded-xl bg-white border border-gray-200 px-4 py-3 text-left text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 hover:border-blue-200"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {messages.map((message, index) => (
              <ChatMessageBubble
                key={index}
                message={message}
                attachmentSnippet={(message as MessageWithFacts).attachmentSnippet}
                citedFacts={(message as MessageWithFacts).cited_facts}
              />
            ))}
            {isPending && (
              <div className="flex justify-start">
                <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-white border border-gray-100 shadow-sm px-4 py-3">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} className="h-4" />
      </div>

      {/* Attachment bar — watch_item / risk_alert context, above the input */}
      {showAttachmentBar && (
        <div className="border-t border-gray-100 bg-white px-6 py-3">
          <ContextCard
            contextType={contextType!}
            searchParams={searchParams}
            report={report}
            facts={facts}
            onPromptClick={setInput}
            onDismiss={dismissAttachment}
          />
        </div>
      )}

      <div className="border-t border-gray-200 bg-white">
        <ChatInput value={input} onChange={setInput} onSubmit={handleSubmit} isLoading={isPending} />
      </div>
    </section>
  )
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────

export default function ChatPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['latestReportId'],
    queryFn: fetchLatestReportId,
    retry: false,
  })

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />
      <main className="flex-1 px-6 py-8">
        {isLoading && (
          <div className="mx-auto max-w-5xl rounded-2xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <div className="animate-pulse flex flex-col items-center">
              <div className="h-8 w-48 bg-gray-200 rounded mb-4" />
              <div className="h-4 w-64 bg-gray-100 rounded" />
            </div>
          </div>
        )}

        {(error || !data?.report_id) && !isLoading && (
          <div className="mx-auto max-w-2xl rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-sm mt-12">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Analyst Chat</p>
            <h1 className="mt-2 text-2xl font-bold text-gray-950">No report available for chat</h1>
            <p className="mt-4 text-sm leading-relaxed text-gray-500 max-w-md mx-auto">
              Chat answers are grounded in report evidence. Open the workspace when a MarketPulseReport is available.
            </p>
            <Link
              to="/workspace"
              className="mt-6 inline-flex rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700"
            >
              Open Workspace →
            </Link>
          </div>
        )}

        {data?.report_id && <ChatConsole reportId={data.report_id} />}
      </main>
    </div>
  )
}
