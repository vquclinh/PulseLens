// Signal breakdown bars — one horizontal bar per signal type showing score and weight
import type { FC } from 'react'
import type { SignalSummary } from '@/types/api'

interface SignalBreakdownProps {
  signals: SignalSummary[]
}

const SignalBreakdown: FC<SignalBreakdownProps> = () => {
  return <div />
}

export default SignalBreakdown
