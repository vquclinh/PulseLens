// Chat message bubble — user/assistant role styling, inline fact_id citation chips
import type { FC } from 'react'
import type { ChatMessage } from '@/types/api'
import type { AttachmentSnippet } from '@/hooks/use-chat'
import CitationChip from './citation-chip'

interface ChatMessageBubbleProps {
  message: ChatMessage
  attachmentSnippet?: AttachmentSnippet
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

const ChatMessageBubble: FC<ChatMessageBubbleProps> = ({ message, attachmentSnippet }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>

      {/* Compact attachment card — only on user messages that had an active attachment */}
      {isUser && attachmentSnippet && (
        <div className="mb-1.5 max-w-[85%] rounded-2xl border border-blue-200 bg-blue-50 px-3.5 py-2.5 text-xs shadow-sm">
          {/* Label row */}
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
            <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
              {attachmentSnippet.label}
            </span>
            {attachmentSnippet.badgeText && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                {attachmentSnippet.badgeText}
              </span>
            )}
          </div>

          {/* Title */}
          <p className="font-semibold leading-snug text-gray-900 line-clamp-2">
            {attachmentSnippet.title}
          </p>

          {/* Body (rationale / summary / quote) */}
          {attachmentSnippet.body && (
            <p className="mt-1 leading-relaxed text-gray-600 line-clamp-2">
              {attachmentSnippet.body}
            </p>
          )}

          {/* Body2 (trigger / secondary detail) */}
          {attachmentSnippet.body2 && (
            <p className="mt-0.5 text-gray-500 line-clamp-1">
              {attachmentSnippet.body2Label && (
                <span className="font-semibold text-gray-600">{attachmentSnippet.body2Label}: </span>
              )}
              {attachmentSnippet.body2}
            </p>
          )}

          {/* Meta footer (counts, entity, confidence, domain) */}
          {attachmentSnippet.meta && (
            <p className="mt-1.5 text-gray-400 text-[10px]">{attachmentSnippet.meta}</p>
          )}
        </div>
      )}

      {/* Message bubble */}
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
