// Tab navigation bar — Overview, Companies(N), Signals(N), News(N), Evidence(N)
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import { useDashboardStore } from '@/store/dashboard-store'

interface TabNavProps {
  report: MarketPulseReport | undefined
}

const TabNav: FC<TabNavProps> = () => {
  return <nav />
}

export default TabNav
