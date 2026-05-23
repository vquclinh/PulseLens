// News feed container — renders chronological list of news items
import type { FC } from 'react'
import type { NewsItem } from '@/types/api'
import NewsItemCard from './news-item'

interface NewsFeedProps {
  items: NewsItem[]
  activeFilters: string[]
}

const NewsFeed: FC<NewsFeedProps> = () => {
  return <div />
}

export default NewsFeed
