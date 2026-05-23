// Evidence table — paginated filterable fact table with highlight-on-click and CSV export
import type { FC } from 'react'
import type { FactObject } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import { useDashboardStore } from '@/store/dashboard-store'

interface EvidenceTableProps {
  facts: FactObject[]
  filters: Record<string, string>
}

const EvidenceTable: FC<EvidenceTableProps> = () => {
  return <div />
}

export default EvidenceTable
