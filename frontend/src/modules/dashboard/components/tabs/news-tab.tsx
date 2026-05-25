// News tab — chronological feed with company/signal-type filter pills
import { FC, useState } from 'react'
import type { MarketPulseReport } from '@/types/api'
import NewsFeed from '../news/news-feed'
import FilterPills from '../news/filter-pills'

interface NewsTabProps {
  report: MarketPulseReport | undefined
}

const NewsTab: FC<NewsTabProps> = ({ report }) => {
  const [activeFilters, setActiveFilters] = useState<string[]>([])

  if (!report) return null

  const companies = [...new Set(report.company_narratives.map((n) => n.company))]

  const sorted = [...report.news_items].sort((a, b) => {
    if (!a.published_date) return 1
    if (!b.published_date) return -1
    return new Date(b.published_date).getTime() - new Date(a.published_date).getTime()
  })

  return (
    <div className="flex flex-col gap-4">
      <FilterPills
        options={companies}
        active={activeFilters}
        onChange={setActiveFilters}
      />
      <NewsFeed items={sorted} activeFilters={activeFilters} />
    </div>
  )
}

export default NewsTab
