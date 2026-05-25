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

const OverviewTab: FC<OverviewTabProps> = ({ report }) => {
  if (!report) return null

  const tickers = report.company_narratives
    .map((n) => n.ticker)
    .filter(Boolean)

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PulseScoreCard report={report} />
        <SignalBreakdown signals={report.top_signals} />
      </div>

      <MarketNarrativeSection narrative={report.market_narrative} />

      <WatchList items={report.market_narrative.watch_list} />

      {report.contradictions.length > 0 && (
        <ContradictionAlerts contradictions={report.contradictions} />
      )}

      <StockPriceContext tickers={tickers} />
    </div>
  )
}

export default OverviewTab
