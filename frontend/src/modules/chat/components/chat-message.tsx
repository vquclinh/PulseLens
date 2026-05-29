// Chat message bubble — user/assistant role styling, numbered citation rendering,
// and a compact "Sources used" section for cited facts.
import type { FC } from 'react'
import { ExternalLink } from 'lucide-react'
import type { ChatMessage, FactObject } from '@/types/api'
import type { AttachmentSnippet } from '@/hooks/use-chat'

interface ChatMessageBubbleProps {
  message: ChatMessage
  attachmentSnippet?: AttachmentSnippet
  citedFacts?: FactObject[]
}

// Matches [1], [2], … [12] — numbered citations produced by the backend.
const CITATION_NUM_RE = /\[(\d{1,2})\]/g

/**
 * Frontend display-only safety net.
 * Strips any raw internal IDs that slipped through the backend sanitizer.
 * Never mutates the underlying message object — display text only.
 * Preserves [N] numbered citations and markdown links [text](url).
 */
function sanitizeDisplayText(text: string): string {
  return text
    // Multi-fact brackets: [fact_abc, fact_def]
    .replace(/\[fact_[a-zA-Z0-9_]+(?:\s*,\s*fact_[a-zA-Z0-9_]+)*\]/g, '')
    // Single fact refs not already converted to numbers
    .replace(/\[fact_[a-zA-Z0-9_]+\]/g, '')
    // Claim refs
    .replace(/\[claim_[a-zA-Z0-9_-]+(?:\s*,\s*[a-zA-Z0-9_-]+)*\]/g, '')
    // Report refs
    .replace(/\[report_[a-zA-Z0-9_-]+\]/g, '')
    // Bare hex hashes ≥8 chars — not followed by "(" to preserve markdown links
    .replace(/\[[a-f0-9]{8,}\](?!\()/g, '')
    // Collapse extra spaces left by removed refs
    .replace(/  +/g, ' ')
    .trim()
}

/** True if the URL points only to a root domain with no meaningful path. */
function isGenericUrl(url: string): boolean {
  try {
    const { pathname } = new URL(url)
    return pathname === '/' || pathname === '' || pathname === '//'
  } catch {
    return false
  }
}

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

/** Replace [N] with small superscript badges inside the message prose.
 *  Runs sanitizeDisplayText first as a safety net for any leaked raw IDs. */
function renderWithNumberedCitations(content: string) {
  content = sanitizeDisplayText(content)
  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  CITATION_NUM_RE.lastIndex = 0
  while ((match = CITATION_NUM_RE.exec(content)) !== null) {
    if (match.index > lastIndex) parts.push(content.slice(lastIndex, match.index))
    parts.push(
      <sup
        key={match.index}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[9px] font-bold text-white ml-0.5 align-middle"
      >
        {match[1]}
      </sup>,
    )
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < content.length) parts.push(content.slice(lastIndex))
  return parts
}

const ChatMessageBubble: FC<ChatMessageBubbleProps> = ({ message, attachmentSnippet, citedFacts }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>

      {/* Compact attachment card — shown on user messages that had an active attachment */}
      {isUser && attachmentSnippet && (
        <div className="mb-1.5 max-w-[85%] rounded-2xl border border-blue-200 bg-blue-50 px-3.5 py-2.5 text-xs shadow-sm">
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
          <p className="font-semibold leading-snug text-gray-900 line-clamp-2">{attachmentSnippet.title}</p>
          {attachmentSnippet.body && (
            <p className="mt-1 leading-relaxed text-gray-600 line-clamp-2">{attachmentSnippet.body}</p>
          )}
          {attachmentSnippet.body2 && (
            <p className="mt-0.5 text-gray-500 line-clamp-1">
              {attachmentSnippet.body2Label && (
                <span className="font-semibold text-gray-600">{attachmentSnippet.body2Label}: </span>
              )}
              {attachmentSnippet.body2}
            </p>
          )}
          {attachmentSnippet.meta && (
            <p className="mt-1.5 text-[10px] text-gray-400">{attachmentSnippet.meta}</p>
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
          <span className="whitespace-pre-wrap">
            {renderWithNumberedCitations(message.content)}
          </span>
        )}
      </div>

      {/* Sources used — assistant messages only, when cited facts are present */}
      {!isUser && citedFacts && citedFacts.length > 0 && (
        <div className="mt-2 max-w-[85%] w-full flex flex-col gap-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
            Sources used
          </p>
          {citedFacts.map((fact, i) => {
            const domain = sourceDomain(fact.source_url)
            const generic = isGenericUrl(fact.source_url)
            return (
              <div
                key={fact.fact_id}
                className="flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm"
              >
                {/* Citation number badge */}
                <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-blue-600 text-[9px] font-bold text-white">
                  {i + 1}
                </span>

                {/* Source details */}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 line-clamp-1">{fact.claim}</p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0 text-gray-500">
                    <span className="font-medium text-gray-700">{domain}</span>
                    <span>·</span>
                    <span>{fact.signal_type.replace(/_/g, ' ')}</span>
                    <span>·</span>
                    <span>{(fact.confidence * 100).toFixed(0)}% conf</span>
                    {generic && (
                      <span className="text-amber-600 font-medium">· domain-only link</span>
                    )}
                  </div>
                </div>

                {/* Open source link */}
                <a
                  href={fact.source_url}
                  target="_blank"
                  rel="noreferrer"
                  title={generic ? 'Domain-only source link' : `Open source: ${fact.source_url}`}
                  className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ChatMessageBubble
