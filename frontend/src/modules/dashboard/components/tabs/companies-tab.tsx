// Companies tab — 2-column grid of 8 company cards + competitive landscape section
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import CompanyCard from '../companies/company-card'
import CompetitiveLandscape from '../companies/competitive-landscape'

interface CompaniesTabProps {
  report: MarketPulseReport | undefined
}

const CompaniesTab: FC<CompaniesTabProps> = () => {
  return <div />
}

export default CompaniesTab
