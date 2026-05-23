// Overview tab — pulse score, signal breakdown, market narrative, watch list, contradictions, stock context
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import PulseScoreCard from '../overview/pulse-score-card'
import SignalBreakdown from '../overview/signal-breakdown'
import MarketNarrativeSection from '../overview/market-narrative'
import WatchList from '../overview/watch-list'
import ContradictionAlerts from '../overview/contradiction-alerts'
import StockPriceContext from '../overview/stock-price-context'

interface OverviewTabProps {
  report: MarketPulseReport | undefined
}

const OverviewTab: FC<OverviewTabProps> = () => {
  return <div />
}

export default OverviewTab
