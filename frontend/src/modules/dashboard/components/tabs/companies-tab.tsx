// Companies tab — 2-column grid of 8 company cards + competitive landscape section
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import CompanyCard from '../companies/company-card'
import CompetitiveLandscape from '../companies/competitive-landscape'

interface CompaniesTabProps {
  report: MarketPulseReport | undefined
}

const CompaniesTab: FC<CompaniesTabProps> = ({ report }) => {
  if (!report) return null

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {report.company_narratives.map((n) => (
          <CompanyCard key={n.ticker} narrative={n} />
        ))}
      </div>

      {report.company_narratives.length > 0 && (
        <CompetitiveLandscape narratives={report.company_narratives} />
      )}
    </div>
  )
}

export default CompaniesTab
