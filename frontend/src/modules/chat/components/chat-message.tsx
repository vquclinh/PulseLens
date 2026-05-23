// Chat message bubble — user/assistant role styling, inline fact_id citation chips
import type { FC } from 'react'
import type { ChatMessage } from '@/types/api'
import CitationChip from './citation-chip'

interface ChatMessageBubbleProps {
  message: ChatMessage
}

const ChatMessageBubble: FC<ChatMessageBubbleProps> = () => {
  return <div />
}

export default ChatMessageBubble
