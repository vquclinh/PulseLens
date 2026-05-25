// Signals tab — collapsible sections for each of the 7 signal types with evidence cards
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import SignalSection from '../signals/signal-section'

interface SignalsTabProps {
  report: MarketPulseReport | undefined
}

const SignalsTab: FC<SignalsTabProps> = ({ report }) => {
  if (!report) return null

  const sorted = [...report.top_signals].sort((a, b) => b.score - a.score)

  return (
    <div className="flex flex-col gap-3">
      {sorted.map((signal) => (
        <SignalSection
          key={signal.signal_type}
          signal={signal}
          claims={[]}
        />
      ))}
    </div>
  )
}

export default SignalsTab
