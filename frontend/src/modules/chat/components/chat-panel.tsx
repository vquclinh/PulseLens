// Collapsible analyst chat panel — fixed right side, query input, message list, citation links
import type { FC } from 'react'
import ChatMessageBubble from './chat-message'
import ChatInput from './chat-input'
import { useDashboardStore } from '@/store/dashboard-store'
import { useChat } from '@/hooks/use-chat'

interface ChatPanelProps {
  reportId: string
}

const ChatPanel: FC<ChatPanelProps> = () => {
  return <aside />
}

export default ChatPanel
