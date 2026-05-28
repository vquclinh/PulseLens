// Inline citation chip — renders [fact_id] as a clickable badge that jumps to Evidence tab
import type { FC } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardStore } from '@/store/dashboard-store'

interface CitationChipProps {
  factId: string
}

const CitationChip: FC<CitationChipProps> = ({ factId }) => {
  const navigate = useNavigate()
  const { setHighlightedFactId, setActiveTab } = useDashboardStore()

  function handleClick() {
    setHighlightedFactId(factId)
    setActiveTab('evidence')
    navigate('/workspace/evidence')
  }

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center font-mono text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5 hover:bg-blue-100 transition-colors"
    >
      [{factId}]
    </button>
  )
}

export default CitationChip
