// Individual news item — tier badge, domain, date, sentiment badge, headline, summary, fact_ids
import type { FC } from 'react'
import type { NewsItem } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import FactIdChip from '@/shared/components/fact-id-chip'
import { formatDate } from '@/lib/utils'

interface NewsItemCardProps {
  item: NewsItem
}

const NewsItemCard: FC<NewsItemCardProps> = ({ item }) => {
  return (
    <article className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-2 flex-wrap">
        <TierBadge tier={item.source_tier} />
        <span className="text-xs text-gray-500">{item.domain}</span>
        {item.published_date && (
          <>
            <span className="text-xs text-gray-400">·</span>
            <span className="text-xs text-gray-400">{formatDate(item.published_date)}</span>
          </>
        )}
        <div className="ml-auto">
          <SentimentBadge sentiment={item.sentiment} />
        </div>
      </div>

      <a
        href={item.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-semibold text-gray-900 hover:text-blue-600 transition-colors"
      >
        {item.headline}
      </a>

      <p className="text-xs text-gray-600 leading-relaxed">{item.summary}</p>

      {item.fact_ids.length > 0 && (
        <div className="flex gap-1.5 flex-wrap pt-0.5 border-t border-gray-100">
          {item.fact_ids.map((fid) => <FactIdChip key={fid} factId={fid} />)}
        </div>
      )}
    </article>
  )
}

export default NewsItemCard
