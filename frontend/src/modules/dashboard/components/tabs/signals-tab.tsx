// Signals tab — collapsible sections for each of the 7 signal types with evidence cards
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import SignalSection from '../signals/signal-section'

interface SignalsTabProps {
  report: MarketPulseReport | undefined
}

const SignalsTab: FC<SignalsTabProps> = () => {
  return <div />
}

export default SignalsTab
