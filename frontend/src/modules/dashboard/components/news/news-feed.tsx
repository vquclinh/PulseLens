// News feed container — renders chronological list of news items
import type { FC } from 'react'
import type { NewsItem } from '@/types/api'
import NewsItemCard from './news-item'

interface NewsFeedProps {
  items: NewsItem[]
  activeFilters: string[]
}

const NewsFeed: FC<NewsFeedProps> = ({ items, activeFilters }) => {
  const filtered = activeFilters.length === 0
    ? items
    : items.filter((item) =>
        activeFilters.some((f) =>
          item.headline.toLowerCase().includes(f.toLowerCase()) ||
          item.domain.toLowerCase().includes(f.toLowerCase()),
        ),
      )

  if (!filtered.length) {
    return (
      <div className="text-center py-12 text-sm text-gray-400">
        No news items match the current filters.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {filtered.map((item) => (
        <NewsItemCard key={item.item_id} item={item} />
      ))}
    </div>
  )
}

export default NewsFeed
