// Dashboard topbar — PulseLens brand, breadcrumb, pulse status badge, score, time window
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'

interface TopbarProps {
  report: MarketPulseReport | undefined
}

const Topbar: FC<TopbarProps> = () => {
  return <header />
}

export default Topbar
