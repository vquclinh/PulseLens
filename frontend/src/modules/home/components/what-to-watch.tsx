import type { SignalType, WatchItem } from '@/types'

const SIGNAL_LABELS: Record<SignalType, string> = {
  strategic_messaging: 'Strategic Messaging',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  investor_signal: 'Investor Signal',
  supplier_risk: 'Supplier Risk',
  news_sentiment: 'News Sentiment',
  hiring_momentum: 'Hiring Momentum',
}

interface WatchCard {
  title: string
  why: string
  evidenceCount: number
}

interface CompanyWatchInput {
  company: string
  ticker: string
  momentum: string
  key_drivers: string[]
  evidenceCount?: number | null
}

interface WhatToWatchProps {
  watchList?: WatchItem[]
  signalFactCounts: Partial<Record<SignalType, number>>
  strongestSignal: SignalType | null
  companies: CompanyWatchInput[]
  onOpenDashboard: () => void
}

function deriveCards(
  watchList: WatchItem[] | undefined,
  signalFactCounts: Partial<Record<SignalType, number>>,
  strongestSignal: SignalType | null,
  companies: CompanyWatchInput[],
): WatchCard[] {
  if (watchList && watchList.length > 0) {
    return watchList.slice(0, 3).map(item => ({
      title: item.title,
      why: item.rationale,
      evidenceCount: item.signals_pointing_there.length,
    }))
  }

  const cards: WatchCard[] = []
  if (strongestSignal) {
    cards.push({
      title: `${SIGNAL_LABELS[strongestSignal]} follow-through`,
      why: 'This is the densest evidence cluster in the latest report. Watch whether new evidence continues to reinforce or dilute that signal.',
      evidenceCount: signalFactCounts[strongestSignal] ?? 0,
    })
  }

  const pricingCount = signalFactCounts.pricing_pressure ?? 0
  if (pricingCount > 0) {
    cards.push({
      title: 'Pricing pressure updates',
      why: 'Pricing evidence can shift quickly in cloud GPU and AI server markets. Monitor whether pricing facts broaden across more sources.',
      evidenceCount: pricingCount,
    })
  }

  const investorCount = signalFactCounts.investor_signal ?? 0
  if (investorCount > 0) {
    cards.push({
      title: 'Investor signal confirmation',
      why: 'Investor-facing disclosures are high-signal evidence. Watch for fresh filings, IR updates, or earnings commentary.',
      evidenceCount: investorCount,
    })
  }

  const topCompany = [...companies]
    .sort((a, b) => (b.evidenceCount ?? 0) - (a.evidenceCount ?? 0))[0]
  if (topCompany && (topCompany.evidenceCount ?? 0) > 0) {
    cards.push({
      title: `${topCompany.company} company lens`,
      why: topCompany.key_drivers[0]
        ? `Latest company narrative highlights ${topCompany.key_drivers[0]}. Watch whether supporting evidence expands.`
        : 'Watch whether company-specific evidence expands in the next report.',
      evidenceCount: topCompany.evidenceCount ?? 0,
    })
  }

  return cards.slice(0, 3)
}

export default function WhatToWatch({
  watchList,
  signalFactCounts,
  strongestSignal,
  companies,
  onOpenDashboard,
}: WhatToWatchProps) {
  const cards = deriveCards(watchList, signalFactCounts, strongestSignal, companies)

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-gray-950">What to Watch</h2>
          <p className="text-sm text-gray-500 mt-1">
            Forward-looking monitor points derived from live watch list data or evidence distribution.
          </p>
        </div>
        <button
          type="button"
          onClick={onOpenDashboard}
          className="text-sm font-semibold text-blue-600 hover:text-blue-700"
        >
          Open workspace →
        </button>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {cards.map(card => (
          <div key={card.title} className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm flex flex-col gap-3">
            <h3 className="text-base font-semibold text-gray-950">{card.title}</h3>
            <p className="text-sm text-gray-600 leading-relaxed">{card.why}</p>
            <div className="mt-auto flex items-center justify-between border-t border-gray-100 pt-3">
              <span className="text-xs text-gray-400">Supporting evidence</span>
              <span className="text-sm font-semibold text-gray-800 tabular-nums">{card.evidenceCount}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
