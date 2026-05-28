import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '@/shared/components/navbar'
import ChatInput from '../components/chat-input'
import ChatMessageBubble from '../components/chat-message'
import { useChat } from '@/hooks/use-chat'
import { fetchLatestReportId } from '@/lib/api-client'

function ChatConsole({ reportId }: { reportId: string }) {
  const { messages, sendMessage, isPending } = useChat(reportId)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

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
      <div className="border-b border-gray-200 px-6 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Analyst Chat</p>
        <h1 className="mt-1 text-2xl font-bold text-gray-950">Ask questions grounded in latest report evidence</h1>
        <p className="mt-1 text-sm text-gray-500">Report ID: <span className="font-mono">{reportId}</span></p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {messages.length === 0 ? (
          <div className="mx-auto mt-12 max-w-xl text-center">
            <p className="text-sm text-gray-500">Try asking about supplier risks, pricing pressure, or company momentum.</p>
            <div className="mt-5 grid gap-2 text-left">
              {[
                'What are the strongest signals in this report?',
                'Which company has the most pricing pressure evidence?',
                'What supplier risks should I monitor next?',
              ].map((question) => (
                <button
                  key={question}
                  onClick={() => setInput(question)}
                  className="rounded-xl bg-blue-50 px-4 py-3 text-left text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((message, index) => (
              <ChatMessageBubble key={index} message={message} />
            ))}
            {isPending && (
              <div className="flex justify-start">
                <div className="flex gap-1 rounded-xl rounded-bl-sm bg-gray-100 px-3.5 py-2.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput value={input} onChange={setInput} onSubmit={handleSubmit} isLoading={isPending} />
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
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="px-6 py-8">
        {isLoading && (
          <div className="mx-auto max-w-5xl rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400 animate-pulse">
            Loading latest report for chat…
          </div>
        )}

        {(error || !data?.report_id) && !isLoading && (
          <div className="mx-auto max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Analyst Chat</p>
            <h1 className="mt-2 text-2xl font-bold text-gray-950">No report available for chat</h1>
            <p className="mt-3 text-sm leading-relaxed text-gray-500">
              Chat answers are grounded in report evidence. Open the workspace when a MarketPulseReport is available.
            </p>
            <Link
              to="/workspace"
              className="mt-6 inline-flex rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
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
