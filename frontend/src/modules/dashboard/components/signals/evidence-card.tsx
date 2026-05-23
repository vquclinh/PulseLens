// Evidence card — tier badge, domain, date, exact quote, fact_id, confidence score
import type { FC } from 'react'
import type { FactObject } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import FactIdChip from '@/shared/components/fact-id-chip'

interface EvidenceCardProps {
  fact: FactObject
}

const EvidenceCard: FC<EvidenceCardProps> = () => {
  return <div />
}

export default EvidenceCard
