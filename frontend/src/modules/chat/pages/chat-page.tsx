import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '@/shared/components/navbar'
import ChatInput from '../components/chat-input'
import ChatMessageBubble from '../components/chat-message'
import { useChat } from '@/hooks/use-chat'
import { fetchLatestReportId, fetchReport, fetchReportFacts } from '@/lib/api-client'
import type { MarketPulseReport, FactObject } from '@/types/api'
import { FileText, Building2, Activity, Tag, BarChart2 } from 'lucide-react'

function ContextCard({
  contextType,
  searchParams,
  report,
  facts,
  onPromptClick
}: {
  contextType: string
  searchParams: URLSearchParams
  report: MarketPulseReport | undefined
  facts: FactObject[] | undefined
  onPromptClick: (p: string) => void
}) {
  let title = 'Chatting about this context'
  let details = null
  let prompts: string[] = []
  let icon = <FileText className="h-5 w-5 text-blue-600" />
  let isValid = false

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
      prompts = [
        'Explain why this fact matters',
        'What other facts support this?',
        'Is there contradictory evidence?'
      ]
    }
  } else if (contextType === 'company') {
    const company = searchParams.get('company')
    if (company && report) {
      isValid = true
      icon = <Building2 className="h-5 w-5 text-blue-600" />
      title = `Chatting about ${company}`
      const companyNarrative = report.company_narratives.find(n => n.company === company || n.ticker === company)
      const count = facts?.filter(f => {
          const e = f.entity.toLowerCase()
          const c = company.toLowerCase()
          return e === c || c.startsWith(e) || e.startsWith(c) || (companyNarrative && e === companyNarrative.ticker.toLowerCase())
      }).length ?? 0
      
      details = (
        <div className="mt-2 text-sm text-gray-600">
          {companyNarrative && <span className="font-medium text-gray-900 mr-2">Ticker: {companyNarrative.ticker}</span>}
          <span>{count} supporting facts</span>
        </div>
      )
      prompts = [
        `Summarize ${company}'s current market read`,
        `Which signals are strongest for ${company}?`,
        'What should I watch next?'
      ]
    }
  } else if (contextType === 'signal') {
    const signal = searchParams.get('signal')
    if (signal) {
      isValid = true
      icon = <Activity className="h-5 w-5 text-blue-600" />
      title = `Chatting about ${signal.replace('_', ' ')}`
      const count = facts?.filter(f => f.signal_type === signal).length ?? 0
      details = (
        <div className="mt-2 text-sm text-gray-600">
          <span>{count} supporting facts</span>
        </div>
      )
      prompts = [
        'Summarize this signal',
        'Which companies are involved?',
        'Show the strongest supporting facts'
      ]
    }
  } else if (contextType === 'pricing') {
    isValid = true
    icon = <Tag className="h-5 w-5 text-blue-600" />
    title = 'Chatting about Pricing Intelligence'
    const count = facts?.filter(f => f.signal_type === 'pricing_pressure').length ?? 0
    details = (
      <div className="mt-2 text-sm text-gray-600">
        <span>{count} pricing pressure facts</span>
      </div>
    )
    prompts = [
      'What pricing pressure signals matter most?',
      'Which providers appear in pricing evidence?',
      'Are any pricing facts weak or noisy?'
    ]
  } else if (contextType === 'report') {
    isValid = true
    icon = <BarChart2 className="h-5 w-5 text-blue-600" />
    title = 'Chatting about latest report'
    details = (
      <div className="mt-2 text-sm text-gray-600">
        <p>Report: <span className="font-mono">{report?.report_id}</span></p>
        <div className="mt-1 flex gap-2 text-xs">
          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-blue-700 font-medium">Score: {report?.pulse_score.toFixed(1)}</span>
          {report?.quality_status === 'PASS' && (
            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 font-medium">PASS</span>
          )}
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">{facts?.length ?? 0} facts</span>
        </div>
      </div>
    )
    prompts = [
      'Give me the executive summary',
      'What are the top risks?',
      'What evidence should I inspect first?'
    ]
  }

  // Only show the fallback message if data is loaded but context wasn't matched
  if (!isValid && report && facts) {
    return (
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm text-center">
        <p className="text-sm font-medium text-gray-700">Context not found in the latest report. You can still ask about the report.</p>
      </div>
    )
  }

  if (!isValid) return null

  return (
    <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50/30 p-5 shadow-sm ring-1 ring-blue-50">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-base font-bold text-gray-900">{title}</h3>
      </div>
      {details}
      <div className="mt-4 flex flex-wrap gap-2">
        {prompts.map(p => (
          <button key={p} onClick={() => {
            onPromptClick(p)
            setTimeout(() => {
              document.getElementById('chat-input-textarea')?.focus()
            }, 10)
          }} className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50 transition-colors shadow-sm">
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}

function ChatConsole({ reportId }: { reportId: string }) {
  const { messages, sendMessage, isPending } = useChat(reportId)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const [searchParams] = useSearchParams()
  const contextType = searchParams.get('context')

  const { data: report } = useQuery({ queryKey: ['report', reportId], queryFn: () => fetchReport(reportId), staleTime: Infinity })
  const { data: facts } = useQuery({ queryKey: ['facts', reportId], queryFn: () => fetchReportFacts(reportId), staleTime: Infinity })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit() {
    const query = input.trim()
    if (!query || isPending) return
    setInput('')
    sendMessage(query)
  }

  return (
    <section className="mx-auto flex h-[calc(100vh-128px)] max-w-5xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 px-6 py-4 flex justify-between items-center bg-white z-10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Analyst Chat</p>
          <h1 className="mt-1 text-2xl font-bold text-gray-950">Ask questions grounded in latest report evidence</h1>
        </div>
        <p className="text-xs text-gray-400">Report ID: <span className="font-mono font-medium">{reportId}</span></p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 bg-slate-50/50">
        {contextType && (
          <ContextCard 
            contextType={contextType}
            searchParams={searchParams}
            report={report}
            facts={facts}
            onPromptClick={setInput}
          />
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
                        setTimeout(() => {
                          document.getElementById('chat-input-textarea')?.focus()
                        }, 10)
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
              <ChatMessageBubble key={index} message={message} />
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

      <div className="border-t border-gray-200 bg-white">
        <ChatInput value={input} onChange={setInput} onSubmit={handleSubmit} isLoading={isPending} />
      </div>
    </section>
  )
}

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
