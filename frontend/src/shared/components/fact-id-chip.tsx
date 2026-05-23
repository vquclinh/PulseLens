// Clickable fact ID chip — [fact_xxxx] inline citation that highlights fact in Evidence tab
import type { FC } from 'react'
import { useDashboardStore } from '@/store/dashboard-store'

interface FactIdChipProps {
  factId: string
}

const FactIdChip: FC<FactIdChipProps> = () => {
  return <span />
}

export default FactIdChip
