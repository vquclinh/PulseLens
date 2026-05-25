// Watch list section (Layer 4) — 3-5 forward indicators with urgency badges and triggers
import type { FC } from 'react'
import type { WatchItem } from '@/types/api'

interface WatchListProps {
  items: WatchItem[]
}

const URGENCY_STYLES: Record<string, { label: string; cls: string }> = {
  this_week:     { label: 'This Week',    cls: 'bg-red-100 text-red-700 border-red-200' },
  next_2_weeks:  { label: 'Next 2 Weeks', cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  this_month:    { label: 'This Month',   cls: 'bg-blue-100 text-blue-700 border-blue-200' },
}

const WatchList: FC<WatchListProps> = ({ items }) => {
  if (!items.length) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Watch List</span>
      <div className="flex flex-col gap-3">
        {items.map((item, i) => {
          const urg = URGENCY_STYLES[item.urgency] ?? URGENCY_STYLES.this_month
          return (
            <div key={i} className="flex flex-col gap-1.5 border-b border-gray-100 pb-3 last:border-b-0 last:pb-0">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium text-gray-900">{item.title}</span>
                <span className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded border ${urg.cls}`}>
                  {urg.label}
                </span>
              </div>
              <p className="text-xs text-gray-500">{item.rationale}</p>
              <p className="text-xs text-gray-700">
                <span className="font-medium text-gray-800">Trigger: </span>{item.trigger}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default WatchList
