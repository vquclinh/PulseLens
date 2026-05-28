import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchReportFacts } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import type { FactObject, MarketPulseReport } from '@/types/api'

interface PricingPageProps {
  report: MarketPulseReport | undefined
}

function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function confidenceLabel(fact: FactObject): string {
  return `${Math.round(fact.confidence * 100)}% confidence`
}

export default function PricingPage({ report }: PricingPageProps) {
  const { data: facts = [], isLoading } = useQuery({
    queryKey: ['workspaceFacts', report?.report_id, 'pricing_pressure'],
    queryFn: () => fetchReportFacts(report!.report_id),
    enabled: !!report?.report_id,
    staleTime: 10 * 60 * 1000,
  })

  const pricingFacts = useMemo(
    () =>
      facts
        .filter((fact) => fact.signal_type === 'pricing_pressure')
        .sort((a, b) => b.confidence - a.confidence),
    [facts],
  )

  if (!report) return null

  return (
    <section className="flex flex-col gap-5">
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Pricing Intelligence</p>
            <h2 className="mt-1 text-2xl font-bold text-gray-950">Pricing pressure evidence</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-600">
              Live pricing-pressure facts extracted from the latest MarketPulseReport. This view only shows
              facts whose signal type is <span className="font-semibold text-gray-800">pricing_pressure</span>.
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-600">
            <span className="font-semibold text-gray-950">{pricingFacts.length}</span> pricing facts
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-sm text-gray-400 animate-pulse">
          Loading pricing evidence…
        </div>
      ) : pricingFacts.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
          <h3 className="text-base font-semibold text-gray-900">No pricing-pressure facts found</h3>
          <p className="mt-2 text-sm text-gray-500">
            The latest report did not include extracted pricing facts. Use Evidence Explorer for all evidence.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pricingFacts.map((fact) => (
            <article key={fact.fact_id} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{fact.entity}</span>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700">Tier {fact.source_tier}</span>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700">{confidenceLabel(fact)}</span>
                <span
                  className={[
                    'rounded-full px-2.5 py-1',
                    fact.sentiment === 'positive' && 'bg-emerald-50 text-emerald-700',
                    fact.sentiment === 'negative' && 'bg-red-50 text-red-700',
                    fact.sentiment === 'neutral' && 'bg-gray-100 text-gray-700',
                  ].filter(Boolean).join(' ')}
                >
                  {fact.sentiment}
                </span>
              </div>
              <h3 className="mt-4 text-base font-semibold leading-snug text-gray-950">{fact.claim}</h3>
              <blockquote className="mt-3 border-l-4 border-blue-200 pl-4 text-sm leading-relaxed text-gray-700">
                “{fact.evidence_quote}”
              </blockquote>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500">
                <a
                  href={fact.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-blue-600 hover:text-blue-700"
                >
                  {sourceDomain(fact.source_url)}
                </a>
                <span>{formatDate(fact.published_date) || 'Date unavailable'}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
