// Sentiment badge — positive/negative/neutral with green/red/gray color coding
import type { FC } from 'react'
import Badge from './badge'

interface SentimentBadgeProps {
  sentiment: 'positive' | 'negative' | 'neutral'
}

const SentimentBadge: FC<SentimentBadgeProps> = ({ sentiment }) => {
  const variantMap = {
    positive: 'success',
    negative: 'danger',
    neutral: 'default',
  } as const

  return <Badge variant={variantMap[sentiment]}>{sentiment}</Badge>
}

export default SentimentBadge
