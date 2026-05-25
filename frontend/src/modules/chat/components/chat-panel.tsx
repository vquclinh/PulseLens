// Collapsible analyst chat panel — fixed right side, query input, message list, citation links
import { FC, useEffect, useRef, useState } from 'react'
import ChatMessageBubble from './chat-message'
import ChatInput from './chat-input'
import { useDashboardStore } from '@/store/dashboard-store'
import { useChat } from '@/hooks/use-chat'

interface ChatPanelProps {
  reportId: string
}

const ChatPanel: FC<ChatPanelProps> = ({ reportId }) => {
  const { setIsChatOpen } = useDashboardStore()
  const { messages, sendMessage, isPending } = useChat(reportId)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit() {
    const q = input.trim()
    if (!q || isPending) return
    setInput('')
    sendMessage(q)
  }

  return (
    <aside className="fixed top-0 right-0 h-full w-96 bg-white border-l border-gray-200 shadow-lg flex flex-col z-20">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
        <div>
          <span className="text-sm font-semibold text-gray-900">Analyst Chat</span>
          <p className="text-[10px] text-gray-400 mt-0.5">Grounded in report evidence</p>
        </div>
        <button
          onClick={() => setIsChatOpen(false)}
          className="text-gray-400 hover:text-gray-600 transition-colors text-lg leading-none"
          aria-label="Close chat"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <div className="text-center py-8 text-xs text-gray-400 flex flex-col gap-2">
            <p>Ask anything about this market report.</p>
            <div className="flex flex-col gap-1.5 mt-2 text-left">
              {[
                'Which companies are gaining competitive position?',
                'What are the top supplier risk signals?',
                'Why is the pulse score rising this week?',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="text-left text-xs text-blue-600 hover:text-blue-700 bg-blue-50 rounded-lg px-3 py-2 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} />
        ))}
        {isPending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-xl rounded-bl-sm px-3.5 py-2.5 flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        isLoading={isPending}
      />
    </aside>
  )
}

export default ChatPanel
