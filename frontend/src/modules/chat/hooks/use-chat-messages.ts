// Local state hook for managing chat message list within the panel
import { useState } from 'react'
import type { ChatMessage } from '@/types/api'

export function useChatMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  function append(message: ChatMessage) {
    setMessages((prev) => [...prev, message])
  }

  function clear() {
    setMessages([])
  }

  return { messages, append, clear }
}
