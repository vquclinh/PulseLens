// Mutation hook for sending chat messages — manages full conversation history
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendChatMessage } from '@/lib/api-client'
import type { ChatMessage, ContextAttachment, FactObject } from '@/types/api'

/**
 * Compact card shown inside the user message bubble when an attachment was sent.
 * All fields except `label` and `title` are optional — render what's available.
 */
export interface AttachmentSnippet {
  label: string          // 'Watch item' | 'Risk alert' | 'Evidence fact' | ...
  title: string          // primary title line (clamped 2 lines)
  badgeText?: string     // e.g. 'This Week', 'investor signal'
  body?: string          // rationale / summary / evidence quote (clamped 2 lines)
  body2?: string         // trigger / secondary detail (clamped 1 line)
  body2Label?: string    // short prefix for body2 ('Trigger', 'Quote', ...)
  meta?: string          // footer: counts, entity+signal, domain+confidence
}

/** Extended message type (frontend-only fields; never sent to backend). */
export type MessageWithFacts = ChatMessage & {
  cited_facts?: FactObject[]
  attachmentSnippet?: AttachmentSnippet
}

type SendPayload = {
  /** Full query sent to the backend — may include a hidden context prefix. */
  query: string
  /** What is shown in the UI as the user's message (defaults to query). */
  displayContent?: string
  /** Compact tag rendered inside the submitted user message bubble. */
  attachmentSnippet?: AttachmentSnippet
  /** Structured attachment forwarded to the backend via ChatRequest. */
  contextAttachment?: ContextAttachment
}

export function useChat(reportId: string) {
  const [messages, setMessages] = useState<MessageWithFacts[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: ({ query, contextAttachment }: SendPayload) =>
      sendChatMessage({
        query,
        report_id: reportId,
        history: messages.slice(-10).map(({ role, content, cited_fact_ids }) => ({
          role,
          content,
          cited_fact_ids: cited_fact_ids ?? null,
        })),
        session_id: sessionId ?? undefined,
        context_attachment: contextAttachment,
      } as Parameters<typeof sendChatMessage>[0]),

    onMutate: ({ query, displayContent, attachmentSnippet }: SendPayload) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content: displayContent ?? query,
          cited_fact_ids: null,
          attachmentSnippet,
        },
      ])
    },

    onSuccess: (data) => {
      setSessionId(data.session_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          cited_fact_ids: data.cited_facts.map((f) => f.fact_id),
          cited_facts: data.cited_facts,
        },
      ])
    },

    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Failed to get a response — please try again.',
          cited_fact_ids: null,
        },
      ])
    },
  })

  return {
    messages,
    /**
     * Send a message.
     * @param query Full text sent to the backend.
     * @param displayContent Shown in the UI (omit to show `query`).
     * @param attachmentSnippet Compact label rendered in the user message bubble.
     * @param contextAttachment Structured data forwarded to the backend.
     */
    sendMessage: (
      query: string,
      displayContent?: string,
      attachmentSnippet?: AttachmentSnippet,
      contextAttachment?: ContextAttachment,
    ) => mutation.mutate({ query, displayContent, attachmentSnippet, contextAttachment }),
    isPending: mutation.isPending,
    sessionId,
  }
}
