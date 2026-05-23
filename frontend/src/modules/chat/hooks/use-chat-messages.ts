// Local state hook for managing chat message list within the panel
import { useState } from 'react'
import type { ChatMessage } from '@/types/api'

export function useChatMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  function append(_message: ChatMessage) {}

  return { messages, append }
}
