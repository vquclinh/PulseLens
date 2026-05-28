interface TrustProvenanceProps {
  reportId: string
  qualityStatus?: string
  evidenceCount: number
  sourceCount: number
  safeVerifiedFactCount: number | null
  isLive: boolean
  factsFallback: boolean
}

export default function TrustProvenance({
  reportId,
  qualityStatus,
  evidenceCount,
  sourceCount,
  safeVerifiedFactCount,
  isLive,
  factsFallback,
}: TrustProvenanceProps) {
  const rows = [
    ['Live backend', isLive ? 'FastAPI' : 'Fallback'],
    ['Quality', qualityStatus ?? (isLive ? 'Live report' : 'Demo baseline')],
    ['Evidence', `${evidenceCount} facts`],
    ['Sources', String(sourceCount)],
    ['SAFE facts', safeVerifiedFactCount == null ? 'Unavailable' : String(safeVerifiedFactCount)],
    ['Fallback', factsFallback ? 'Active' : 'No fallback active'],
  ]

  return (
    <section className="bg-white border border-gray-200 rounded-2xl px-5 py-4 shadow-sm flex items-center gap-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-950">Trust & Data Provenance</h2>
          <p className="text-xs text-gray-500 mt-0.5">Frontend reads FastAPI; backend reads Supabase/Postgres.</p>
        </div>
      </div>
      <div className="flex flex-1 items-center gap-2 overflow-x-auto">
        {rows.map(([label, value]) => (
          <div key={label} className="min-w-[118px] rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">{label}</div>
            <div className="mt-1 text-sm font-semibold text-gray-800 break-words">{value}</div>
          </div>
        ))}
      </div>
      <div className="text-[11px] text-gray-400 max-w-[180px]">
        Report <span className="font-mono">{reportId}</span>
      </div>
    </section>
  )
}
