// Zustand store — active dashboard tab, chat panel visibility, highlighted fact ID
import { create } from 'zustand'
import type { MarketPulseReport } from '@/types/api'

interface DashboardState {
  activeTab: string
  isChatOpen: boolean
  highlightedFactId: string | null
  report: MarketPulseReport | null
  setActiveTab: (tab: string) => void
  setIsChatOpen: (open: boolean) => void
  setHighlightedFactId: (id: string | null) => void
  setReport: (report: MarketPulseReport | null) => void
}

export const useDashboardStore = create<DashboardState>()(() => ({
  activeTab: 'overview',
  isChatOpen: false,
  highlightedFactId: null,
  report: null,
  setActiveTab: () => {},
  setIsChatOpen: () => {},
  setHighlightedFactId: () => {},
  setReport: () => {},
}))
