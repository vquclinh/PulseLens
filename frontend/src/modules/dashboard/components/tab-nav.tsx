// Tab navigation bar — Overview, Companies(N), Signals(N), News(N), Evidence(N)
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import { useDashboardStore } from '@/store/dashboard-store'
import { cn } from '@/lib/utils'

interface TabNavProps {
  report: MarketPulseReport | undefined
}

const TabNav: FC<TabNavProps> = ({ report }) => {
  const { activeTab, setActiveTab } = useDashboardStore()

  const tabs = [
    { id: 'overview',   label: 'Overview',   count: null },
    { id: 'companies',  label: 'Companies',  count: report?.company_narratives.length ?? null },
    { id: 'signals',    label: 'Signals',    count: report?.top_signals.length ?? null },
    { id: 'news',       label: 'News',       count: report?.news_items.length ?? null },
    { id: 'evidence',   label: 'Evidence',   count: report?.evidence_count ?? null },
  ]

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-[57px] z-10">
      <div className="max-w-7xl mx-auto px-6 flex gap-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5',
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            )}
          >
            {tab.label}
            {tab.count !== null && (
              <span
                className={cn(
                  'text-[10px] font-semibold rounded-full px-1.5 py-0.5',
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-500',
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>
    </nav>
  )
}

export default TabNav
