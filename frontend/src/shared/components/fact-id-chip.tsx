// Clickable fact ID chip — [fact_xxxx] inline citation that highlights fact in Evidence tab
import type { FC } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardStore } from '@/store/dashboard-store'

interface FactIdChipProps {
  factId: string
}

const FactIdChip: FC<FactIdChipProps> = ({ factId }) => {
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
      className="inline-flex items-center font-mono text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5 hover:bg-blue-100 transition-colors cursor-pointer"
    >
      [{factId}]
    </button>
  )
}

export default FactIdChip
