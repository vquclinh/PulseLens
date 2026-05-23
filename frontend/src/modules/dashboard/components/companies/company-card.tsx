// Company card — initial circle, name, ticker, momentum badge, score bar, narrative, stock line
import type { FC } from 'react'
import type { CompanyNarrative } from '@/types/api'
import MomentumBadge from '@/shared/components/momentum-badge'
import { useDashboardStore } from '@/store/dashboard-store'

interface CompanyCardProps {
  narrative: CompanyNarrative
}

const CompanyCard: FC<CompanyCardProps> = () => {
  return <div />
}

export default CompanyCard
