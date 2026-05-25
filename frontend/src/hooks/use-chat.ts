// Mutation hook for sending chat messages — manages full conversation history
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendChatMessage } from '@/lib/api-client'
import type { ChatMessage, FactObject } from '@/types/api'

type MessageWithFacts = ChatMessage & { cited_facts?: FactObject[] }

export function useChat(reportId: string) {
  const [messages, setMessages] = useState<MessageWithFacts[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (query: string) =>
      sendChatMessage({
        query,
        report_id: reportId,
        history: messages.slice(-10).map(({ role, content, cited_fact_ids }) => ({
          role,
          content,
          cited_fact_ids: cited_fact_ids ?? null,
        })),
        session_id: sessionId ?? undefined,
      } as Parameters<typeof sendChatMessage>[0]),
    onMutate: (query) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: query, cited_fact_ids: null },
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
    sendMessage: (query: string) => mutation.mutate(query),
    isPending: mutation.isPending,
    sessionId,
  }
}
