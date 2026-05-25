// Evidence tab — filterable fact table with export, highlighting, and pagination
import { FC, useState } from 'react'
import type { MarketPulseReport } from '@/types/api'
import { useQuery } from '@tanstack/react-query'
import { fetchReportFacts } from '@/lib/api-client'
import EvidenceTable from '../evidence/evidence-table'
import EvidenceFilters from '../evidence/evidence-filters'

interface EvidenceTabProps {
  report: MarketPulseReport | undefined
}

const EvidenceTab: FC<EvidenceTabProps> = ({ report }) => {
  const [filters, setFilters] = useState<Record<string, string>>({})

  const { data: facts = [], isLoading } = useQuery({
    queryKey: ['facts', report?.report_id],
    queryFn: () => fetchReportFacts(report!.report_id),
    enabled: !!report?.report_id,
    staleTime: 10 * 60 * 1000,
  })

  if (!report) return null

  function handleFilterChange(k: string, v: string) {
    setFilters((prev) => ({ ...prev, [k]: v }))
  }

  return (
    <div className="flex flex-col gap-4">
      <EvidenceFilters filters={filters} onChange={handleFilterChange} />
      {isLoading ? (
        <div className="text-center py-8 text-sm text-gray-400 animate-pulse">Loading evidence…</div>
      ) : facts.length > 0 ? (
        <EvidenceTable facts={facts} filters={filters} />
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-center text-sm text-gray-400">
          No evidence facts found for this report.
        </div>
      )}
    </div>
  )
}

export default EvidenceTab
