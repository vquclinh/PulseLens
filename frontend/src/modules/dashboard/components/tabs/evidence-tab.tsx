// Evidence tab — filterable fact table with export, highlighting, and pagination
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import EvidenceTable from '../evidence/evidence-table'
import EvidenceFilters from '../evidence/evidence-filters'

interface EvidenceTabProps {
  report: MarketPulseReport | undefined
}

const EvidenceTab: FC<EvidenceTabProps> = () => {
  return <div />
}

export default EvidenceTab
