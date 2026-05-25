// Evidence table — paginated filterable fact table with highlight-on-click and CSV export
import { FC, useState } from 'react'
import type { FactObject } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import { useDashboardStore } from '@/store/dashboard-store'
import { formatDate } from '@/lib/utils'

const PAGE_SIZE = 20

interface EvidenceTableProps {
  facts: FactObject[]
  filters: Record<string, string>
}

const EvidenceTable: FC<EvidenceTableProps> = ({ facts, filters }) => {
  const { highlightedFactId, setHighlightedFactId } = useDashboardStore()
  const [page, setPage] = useState(0)

  const filtered = facts.filter((f) => {
    if (filters.entity && !f.entity.toLowerCase().includes(filters.entity.toLowerCase())) return false
    if (filters.signal_type && f.signal_type !== filters.signal_type) return false
    if (filters.tier && f.source_tier !== Number(filters.tier)) return false
    if (filters.sentiment && f.sentiment !== filters.sentiment) return false
    if (filters.min_confidence && f.confidence < Number(filters.min_confidence)) return false
    return true
  })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function exportCsv() {
    const header = 'fact_id,entity,signal_type,sentiment,confidence,tier,date,claim\n'
    const rows = filtered.map((f) =>
      [f.fact_id, f.entity, f.signal_type, f.sentiment, f.confidence, f.source_tier, f.published_date ?? '', `"${f.claim.replace(/"/g, '""')}"`].join(','),
    )
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'evidence.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{filtered.length} facts</span>
        <button
          onClick={exportCsv}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Fact ID</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Entity</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Signal</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Tier</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Sentiment</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Date</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Claim</th>
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((f) => {
              const isHighlighted = f.fact_id === highlightedFactId
              return (
                <tr
                  key={f.fact_id}
                  onClick={() => setHighlightedFactId(isHighlighted ? null : f.fact_id)}
                  className={`border-t border-gray-100 cursor-pointer transition-colors ${
                    isHighlighted ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="py-2 px-3 font-mono text-blue-600 whitespace-nowrap">{f.fact_id}</td>
                  <td className="py-2 px-3 text-gray-700 whitespace-nowrap">{f.entity}</td>
                  <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{f.signal_type.replace(/_/g, ' ')}</td>
                  <td className="py-2 px-3"><TierBadge tier={f.source_tier} /></td>
                  <td className="py-2 px-3"><SentimentBadge sentiment={f.sentiment} /></td>
                  <td className="py-2 px-3 text-gray-500 whitespace-nowrap">{formatDate(f.published_date)}</td>
                  <td className="py-2 px-3 text-gray-700 max-w-xs truncate">{f.claim}</td>
                  <td className="py-2 px-3 tabular-nums text-gray-500">{f.confidence.toFixed(2)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-40 px-2 py-1 rounded border border-gray-200"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-40 px-2 py-1 rounded border border-gray-200"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

export default EvidenceTable
