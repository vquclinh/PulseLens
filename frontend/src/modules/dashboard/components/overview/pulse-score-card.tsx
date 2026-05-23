// Pulse score card — large score number, status badge, trend delta, 7-day sparkline
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import Sparkline from '@/shared/components/sparkline'

interface PulseScoreCardProps {
  report: MarketPulseReport
}

const PulseScoreCard: FC<PulseScoreCardProps> = () => {
  return <div />
}

export default PulseScoreCard
