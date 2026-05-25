// Chat text input with send button and loading state
import type { FC } from 'react'
import { useRef } from 'react'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  isLoading: boolean
}

const ChatInput: FC<ChatInputProps> = ({ value, onChange, onSubmit, isLoading }) => {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isLoading && value.trim()) onSubmit()
    }
  }

  return (
    <div className="flex items-end gap-2 p-3 border-t border-gray-200 bg-white">
      <textarea
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about signals, companies, risks…"
        rows={2}
        disabled={isLoading}
        className="flex-1 resize-none text-sm text-gray-800 placeholder-gray-400 border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60"
      />
      <button
        onClick={onSubmit}
        disabled={isLoading || !value.trim()}
        className="shrink-0 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {isLoading ? (
          <span className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1 h-1 rounded-full bg-white animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </span>
        ) : (
          'Send'
        )}
      </button>
    </div>
  )
}

export default ChatInput
