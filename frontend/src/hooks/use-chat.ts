// TanStack Query mutation hook for sending chat messages and managing conversation history
import { useMutation } from '@tanstack/react-query'
import { sendChatMessage } from '@/lib/api-client'
import type { ChatMessage } from '@/types/api'

export function useChat(_reportId: string) {
  const messages: ChatMessage[] = []

  const mutation = useMutation({
    mutationFn: sendChatMessage,
  })

  return {
    messages,
    sendMessage: mutation.mutate,
    isPending: mutation.isPending,
  }
}
