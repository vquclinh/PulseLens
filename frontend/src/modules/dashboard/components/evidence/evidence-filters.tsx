// Evidence filter controls — dropdowns for company, signal type, tier, sentiment, min confidence
import type { FC } from 'react'

interface EvidenceFiltersProps {
  filters: Record<string, string>
  onChange: (k: string, v: string) => void
}

const EvidenceFilters: FC<EvidenceFiltersProps> = () => {
  return <div />
}

export default EvidenceFilters
