// Individual news item — tier badge, domain, date, sentiment badge, headline, summary, fact_ids
import type { FC } from 'react'
import type { NewsItem } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import FactIdChip from '@/shared/components/fact-id-chip'

interface NewsItemCardProps {
  item: NewsItem
}

const NewsItemCard: FC<NewsItemCardProps> = () => {
  return <article />
}

export default NewsItemCard
