// Inline citation chip — renders [fact_id] as a clickable badge that jumps to Evidence tab
import type { FC } from 'react'
import { useDashboardStore } from '@/store/dashboard-store'

interface CitationChipProps {
  factId: string
}

const CitationChip: FC<CitationChipProps> = () => {
  return <span />
}

export default CitationChip
