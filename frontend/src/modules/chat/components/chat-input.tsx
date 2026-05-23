// Chat text input with send button and loading state
import type { FC } from 'react'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  isLoading: boolean
}

const ChatInput: FC<ChatInputProps> = () => {
  return <div />
}

export default ChatInput
