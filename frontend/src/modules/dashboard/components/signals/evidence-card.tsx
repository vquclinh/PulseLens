// Evidence card — tier badge, domain, date, exact quote, fact_id, confidence score
import type { FC } from 'react'
import type { FactObject } from '@/types/api'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import FactIdChip from '@/shared/components/fact-id-chip'
import { formatDate } from '@/lib/utils'

interface EvidenceCardProps {
  fact: FactObject
}

const EvidenceCard: FC<EvidenceCardProps> = ({ fact }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-2 flex-wrap">
        <TierBadge tier={fact.source_tier} />
        <span className="text-xs text-gray-500">
          {(() => { try { return new URL(fact.source_url).hostname } catch { return fact.source_url } })()}
        </span>
        {fact.published_date && (
          <>
            <span className="text-xs text-gray-400">·</span>
            <span className="text-xs text-gray-400">{formatDate(fact.published_date)}</span>
          </>
        )}
        <div className="ml-auto">
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>

      <p className="text-xs text-gray-700 leading-relaxed border-l-2 border-gray-200 pl-2.5 italic">
        "{fact.evidence_quote}"
      </p>

      <div className="flex items-center gap-2 pt-0.5 flex-wrap">
        <FactIdChip factId={fact.fact_id} />
        <span className="text-[10px] text-gray-400">{fact.entity}</span>
        <span className="text-[10px] text-gray-400 ml-auto">
          confidence {fact.confidence.toFixed(2)}
        </span>
      </div>
    </div>
  )
}

export default EvidenceCard
