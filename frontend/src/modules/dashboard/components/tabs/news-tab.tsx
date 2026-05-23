// News tab — chronological feed with company/signal-type filter pills
import type { FC } from 'react'
import type { MarketPulseReport } from '@/types/api'
import NewsFeed from '../news/news-feed'
import FilterPills from '../news/filter-pills'

interface NewsTabProps {
  report: MarketPulseReport | undefined
}

const NewsTab: FC<NewsTabProps> = () => {
  return <div />
}

export default NewsTab
