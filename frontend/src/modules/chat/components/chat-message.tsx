// Chat message bubble — user/assistant role styling, inline fact_id citation chips
import type { FC } from 'react'
import type { ChatMessage } from '@/types/api'
import CitationChip from './citation-chip'

interface ChatMessageBubbleProps {
  message: ChatMessage
}

const FACT_REF_RE = /\[(fact_[A-Za-z0-9_]+)\]/g

function renderWithCitations(content: string) {
  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  FACT_REF_RE.lastIndex = 0
  while ((match = FACT_REF_RE.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index))
    }
    parts.push(<CitationChip key={match.index} factId={match[1]} />)
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }

  return parts
}

const ChatMessageBubble: FC<ChatMessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        }`}
      >
        {isUser ? (
          message.content
        ) : (
          <span className="whitespace-pre-wrap">{renderWithCitations(message.content)}</span>
        )}
      </div>
    </div>
  )
}

export default ChatMessageBubble
