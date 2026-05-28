import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '@/shared/components/navbar'
import SectorCard from '@/modules/sector-select/components/sector-card'
import Hero from '../components/hero'
import MarketSnapshot from '../components/market-snapshot'
import SignalCoverage from '../components/signal-coverage'
import CompanyCoverage from '../components/company-coverage'
import FactPreview from '../components/fact-preview'
import HowItWorks from '../components/how-it-works'
import {
  DEMO_REPORT_ID,
  DEMO_DATE,
  DEMO_PULSE,
  DEMO_COUNTS,
  DEMO_SIGNAL_BREAKDOWN,
  DEMO_COMPANIES,
  DEMO_FACTS,
} from '../lib/demo-baseline'
import { fetchLatestReportId, fetchReport } from '@/lib/api-client'
import type { SignalType } from '@/types'

const SECTORS = [
  { name: 'US AI Hardware',     description: 'Nvidia, AMD, Intel, Broadcom, Supermicro, Dell, HPE, Micron', isLive: true,  slug: 'us-ai-hardware' },
  { name: 'US Cybersecurity',   description: 'Palo Alto, CrowdStrike, Fortinet, Zscaler',                  isLive: false, slug: '' },
  { name: 'Cloud GPU Infra',    description: 'AWS, Azure, GCP, CoreWeave, Lambda',                         isLive: false, slug: '' },
  { name: 'EV Supply Chain',    description: 'Tesla, BYD, LG Energy, CATL',                               isLive: false, slug: '' },
  { name: 'Vietnam E-commerce', description: 'Shopee, Tiki, Lazada, VinCommerce',                          isLive: false, slug: '' },
  { name: 'Biotech / Pharma',   description: 'Moderna, BioNTech, Vertex, Regeneron',                      isLive: false, slug: '' },
]

export default function HomePage() {
  const navigate = useNavigate()

  const { data: latestMeta } = useQuery({
    queryKey: ['latestReportId'],
    queryFn: fetchLatestReportId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const reportId = latestMeta?.report_id

  const { data: report } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: !!reportId,
    retry: false,
  })

  const isLive = !!report
  const pulseScore = report?.pulse_score ?? DEMO_PULSE.score
  const pulseStatus = report?.pulse_status ?? DEMO_PULSE.status
  const pulseConfidence = report?.pulse_confidence ?? DEMO_PULSE.confidence
  const evidenceCount = report?.evidence_count ?? DEMO_COUNTS.evidenceCount
  const sourceCount = report?.source_count ?? DEMO_COUNTS.sourceCount
  const displayReportId = report?.report_id ?? DEMO_REPORT_ID
  const displayDate = report?.generated_at?.slice(0, 10) ?? DEMO_DATE

  const signalBreakdown: Partial<Record<SignalType, number>> =
    report?.signal_breakdown
      ? (report.signal_breakdown as Partial<Record<SignalType, number>>)
      : DEMO_SIGNAL_BREAKDOWN

  const companies =
    report?.company_narratives?.map(n => ({
      company: n.company,
      ticker: n.ticker,
      momentum: n.momentum,
      key_drivers: n.key_drivers ?? [],
    })) ?? DEMO_COMPANIES

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Navbar />
      <Hero />

      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col gap-10">

        {/* Demo baseline banner — only when API is unavailable */}
        {!isLive && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-800 flex items-center gap-2">
            <span className="font-semibold">Demo baseline</span>
            <span className="text-amber-600">—</span>
            <span>Showing locked Sprint 8 run · <span className="font-mono">{DEMO_REPORT_ID}</span> · {DEMO_DATE}</span>
            <span className="ml-auto text-amber-600">Start the backend to load live data</span>
          </div>
        )}

        {/* Market snapshot */}
        <MarketSnapshot
          pulseScore={pulseScore}
          pulseStatus={pulseStatus}
          pulseConfidence={pulseConfidence}
          evidenceCount={evidenceCount}
          sourceCount={sourceCount}
          verifiedClaimsCount={DEMO_COUNTS.verifiedClaimsCount}
          isLive={isLive}
          reportId={displayReportId}
          generatedAt={displayDate}
        />

        {/* Signal coverage + company coverage side by side */}
        <div className="grid grid-cols-2 gap-6">
          <SignalCoverage signalBreakdown={signalBreakdown} />
          <CompanyCoverage companies={companies} />
        </div>

        {/* Featured insights */}
        <FactPreview facts={DEMO_FACTS} reportId={DEMO_REPORT_ID} />

        {/* How it works */}
        <HowItWorks />

        {/* Sector grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Explore Markets</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                One market is live for this demo. Additional sectors are being instrumented.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {SECTORS.map(s => (
              <SectorCard
                key={s.name}
                name={s.name}
                description={s.description}
                isLive={s.isLive}
                onClick={s.isLive ? () => navigate(`/dashboard/${s.slug}`) : undefined}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-gray-200 pt-6 pb-2 flex items-center justify-between">
          <span className="text-xs text-gray-400">
            © 2026 PulseLens · Market intelligence for the AI hardware sector
          </span>
          <span className="text-xs text-gray-400">
            Data context only — not investment advice
          </span>
        </footer>

      </div>
    </div>
  )
}
