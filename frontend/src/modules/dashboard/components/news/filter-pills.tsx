// Filter pills — company and signal type toggles for the news feed
import type { FC } from 'react'
import { cn } from '@/lib/utils'

interface FilterPillsProps {
  options: string[]
  active: string[]
  onChange: (filters: string[]) => void
}

const FilterPills: FC<FilterPillsProps> = ({ options, active, onChange }) => {
  function toggle(opt: string) {
    onChange(
      active.includes(opt) ? active.filter((a) => a !== opt) : [...active, opt],
    )
  }

  if (!options.length) return null

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isActive = active.includes(opt)
        return (
          <button
            key={opt}
            onClick={() => toggle(opt)}
            className={cn(
              'text-xs font-medium px-2.5 py-1 rounded-full border transition-colors',
              isActive
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400 hover:text-blue-600',
            )}
          >
            {opt}
          </button>
        )
      })}
      {active.length > 0 && (
        <button
          onClick={() => onChange([])}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors px-1"
        >
          Clear
        </button>
      )}
    </div>
  )
}

export default FilterPills
