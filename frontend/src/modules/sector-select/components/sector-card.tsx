// Individual sector card — shows name, description, live/coming-soon badge, click handler
import type { FC } from 'react'

interface SectorCardProps {
  name: string
  description: string
  isLive: boolean
  onClick?: () => void
}

const SectorCard: FC<SectorCardProps> = ({ name, description, isLive, onClick }) => {
  return (
    <div
      onClick={isLive ? onClick : undefined}
      className={[
        'rounded-lg border p-6 flex flex-col gap-2 transition-all',
        isLive
          ? 'border-blue-500 bg-white shadow-sm cursor-pointer hover:shadow-md hover:border-blue-600'
          : 'border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed',
      ].join(' ')}
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold text-gray-900 text-sm">{name}</span>
        {isLive ? (
          <span className="flex items-center gap-1 text-xs font-medium text-green-600">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            Live
          </span>
        ) : (
          <span className="text-xs font-medium text-gray-400">Coming soon</span>
        )}
      </div>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  )
}

export default SectorCard
