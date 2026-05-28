import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import Navbar from '@/shared/components/navbar'
import SectorCard from '@/modules/sector-select/components/sector-card'
import Hero from '../components/hero'
import MarketSnapshot from '../components/market-snapshot'
import SignalCoverage from '../components/signal-coverage'
import CompanyCoverage from '../components/company-coverage'
import FactPreview from '../components/fact-preview'
import type { DisplayFact } from '../components/fact-preview'
import HowItWorks from '../components/how-it-works'
import TrustProvenance from '../components/trust-provenance'
import WhatToWatch from '../components/what-to-watch'
import {
  DEMO_REPORT_ID,
  DEMO_DATE,
  DEMO_PULSE,
  DEMO_COUNTS,
  DEMO_SIGNAL_FACT_COUNTS,
  DEMO_COMPANIES,
  DEMO_FACTS,
} from '../lib/demo-baseline'
import { fetchLatestReportId, fetchReport, fetchReportFacts } from '@/lib/api-client'
import type { SignalType } from '@/types'

const SECTORS = [
  { name: 'US AI Hardware',     description: 'Nvidia, AMD, Intel, Broadcom, Supermicro, Dell, HPE, Micron', isLive: true,  slug: 'us-ai-hardware' },
  { name: 'US Cybersecurity',   description: 'Palo Alto, CrowdStrike, Fortinet, Zscaler',                  isLive: false, slug: '' },
  { name: 'Cloud GPU Infra',    description: 'AWS, Azure, GCP, CoreWeave, Lambda',                         isLive: false, slug: '' },
  { name: 'EV Supply Chain',    description: 'Tesla, BYD, LG Energy, CATL',                               isLive: false, slug: '' },
  { name: 'Vietnam E-commerce', description: 'Shopee, Tiki, Lazada, VinCommerce',                          isLive: false, slug: '' },
  { name: 'Biotech / Pharma',   description: 'Moderna, BioNTech, Vertex, Regeneron',                      isLive: false, slug: '' },
]

const SIGNAL_ORDER: SignalType[] = [
  'strategic_messaging',
  'product_launch',
  'pricing_pressure',
  'investor_signal',
  'supplier_risk',
  'news_sentiment',
  'hiring_momentum',
]

export default function HomePage() {
  const navigate = useNavigate()
  const [activeSignal, setActiveSignal] = useState<SignalType | 'all'>('all')
  const [activeCompany, setActiveCompany] = useState<string>('all')
  const [factSortMode, setFactSortMode] = useState<'confidence' | 'tier'>('confidence')

  const { data: latestMeta, isError: latestIdError, isLoading: latestIdLoading } = useQuery({
    queryKey: ['latestReportId'],
    queryFn: fetchLatestReportId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const reportId = latestMeta?.report_id

  const { data: report, isError: reportError, isLoading: reportLoading } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: !!reportId,
    retry: false,
  })

  const { data: facts, isError: factsError, isLoading: factsLoading } = useQuery({
    queryKey: ['reportFacts', reportId],
    queryFn: () => fetchReportFacts(reportId!),
    enabled: !!reportId,
    retry: false,
  })

  const isLive = !!report
  const reportFallback = latestIdError || reportError
  const factsFallback = factsError || reportFallback

  if (!report && !reportFallback && (latestIdLoading || reportLoading || !latestMeta)) {
    return (
      <div className="min-h-screen bg-gray-50 text-gray-900">
        <Navbar />
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="bg-white border border-gray-200 rounded-xl p-6 text-sm text-gray-500">
            Loading latest PulseLens report from the backend...
          </div>
        </div>
      </div>
    )
  }
  const pulseScore = report?.pulse_score ?? DEMO_PULSE.score
  const pulseStatus = report?.pulse_status ?? DEMO_PULSE.status
  const pulseConfidence = report?.pulse_confidence ?? DEMO_PULSE.confidence
  const evidenceCount = report?.evidence_count ?? DEMO_COUNTS.evidenceCount
  const sourceCount = report?.source_count ?? DEMO_COUNTS.sourceCount
  const displayReportId = report?.report_id ?? DEMO_REPORT_ID
  const displayDate = report?.generated_at?.slice(0, 10) ?? DEMO_DATE

  // Signal fact counts: integer counts per signal type from /facts (not float scores from signal_breakdown)
  const signalFactCounts: Partial<Record<SignalType, number>> = facts
    ? facts.reduce((acc, f) => {
        acc[f.signal_type] = (acc[f.signal_type] ?? 0) + 1
        return acc
      }, {} as Partial<Record<SignalType, number>>)
    : factsFallback
    ? DEMO_SIGNAL_FACT_COUNTS
    : {}

  // Average fact confidence from /facts endpoint
  const avgFactConfidence: number | null = facts && facts.length > 0
    ? facts.reduce((sum, f) => sum + f.confidence, 0) / facts.length
    : null
  const safeVerifiedFactCount = facts
    ? facts.filter(f => f.safe_verified).length
    : null

  // Accepted doc count from audit_summary (for HowItWorks step 1)
  const acceptedDocCount = report?.audit_summary?.accepted_doc_count ?? DEMO_COUNTS.evidenceCount

  const candidateFacts: DisplayFact[] = facts ?? (factsFallback ? DEMO_FACTS : [])
  const companyEvidenceCounts = candidateFacts.reduce((acc, fact) => {
    acc[fact.entity] = (acc[fact.entity] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Featured facts are live when available, with fallback only on API failure.
  const activeCompanyKey = activeCompany.toLowerCase()
  const filteredFacts = candidateFacts
    .filter(f => activeSignal === 'all' || f.signal_type === activeSignal)
    .filter(f => activeCompany === 'all' || f.entity.toLowerCase() === activeCompanyKey)
    .sort((a, b) => {
      if (factSortMode === 'tier') {
        return a.source_tier - b.source_tier || b.confidence - a.confidence
      }
      return b.confidence - a.confidence || a.source_tier - b.source_tier
    })
    .slice(0, 4)

  const strongestSignal = SIGNAL_ORDER.reduce<SignalType | null>((best, signal) => {
    if (best == null) return signal
    return (signalFactCounts[signal] ?? 0) > (signalFactCounts[best] ?? 0) ? signal : best
  }, null)
  const strongestSignalWithEvidence =
    strongestSignal && (signalFactCounts[strongestSignal] ?? 0) > 0 ? strongestSignal : null

  const companies =
    report?.company_narratives?.map(n => ({
      company: n.company,
      ticker: n.ticker,
      momentum: n.momentum,
      key_drivers: n.key_drivers ?? [],
      evidenceCount: companyEvidenceCounts[n.company] ?? 0,
    })) ?? DEMO_COMPANIES

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Navbar />
      <Hero
        pulseScore={pulseScore}
        pulseStatus={pulseStatus}
        pulseConfidence={pulseConfidence}
        qualityStatus={report?.quality_status}
        evidenceCount={evidenceCount}
        sourceCount={sourceCount}
        generatedAt={displayDate}
        isLive={isLive}
      />

      <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col gap-12">

        {/* Demo baseline banner — only when API is unavailable */}
        {reportFallback && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-800 flex items-center gap-2">
            <span className="font-semibold">Demo baseline</span>
            <span className="text-amber-600">—</span>
            <span>Showing locked Sprint 8 run · <span className="font-mono">{DEMO_REPORT_ID}</span> · {DEMO_DATE}</span>
            <span className="ml-auto text-amber-600">Start the backend to load live data</span>
          </div>
        )}

        <TrustProvenance
          reportId={displayReportId}
          qualityStatus={report?.quality_status}
          evidenceCount={evidenceCount}
          sourceCount={sourceCount}
          safeVerifiedFactCount={safeVerifiedFactCount}
          isLive={isLive}
          factsFallback={factsFallback}
        />

        {/* Market snapshot */}
        <MarketSnapshot
          pulseScore={pulseScore}
          pulseStatus={pulseStatus}
          pulseConfidence={pulseConfidence}
          evidenceCount={evidenceCount}
          sourceCount={sourceCount}
          avgFactConfidence={avgFactConfidence}
          safeVerifiedFactCount={safeVerifiedFactCount}
          factsLoading={isLive && factsLoading && !facts}
          factsUnavailable={factsFallback}
          qualityStatus={report?.quality_status}
          isLive={isLive}
          generatedAt={displayDate}
        />

        {/* Signal coverage + company coverage side by side */}
        <div className="grid grid-cols-2 gap-6">
          <SignalCoverage
            signalFactCounts={signalFactCounts}
            activeSignal={activeSignal}
            onSignalChange={setActiveSignal}
            isFallback={factsFallback}
            isLoading={isLive && factsLoading && !facts}
          />
          <CompanyCoverage
            companies={companies}
            activeCompany={activeCompany}
            onCompanyChange={setActiveCompany}
            isFallback={reportFallback}
          />
        </div>

        {/* Featured insights — live facts when available, demo fallback labeled */}
        <FactPreview
          facts={filteredFacts}
          activeSignal={activeSignal}
          activeCompany={activeCompany}
          sortMode={factSortMode}
          onSortChange={setFactSortMode}
          isFallback={factsFallback}
          isLoading={isLive && factsLoading && !facts}
        />

        <WhatToWatch
          watchList={report?.market_narrative?.watch_list}
          signalFactCounts={signalFactCounts}
          strongestSignal={strongestSignalWithEvidence}
          companies={companies}
          onOpenDashboard={() => navigate('/workspace')}
        />

        {/* How it works */}
        <HowItWorks
          sourceCount={sourceCount}
          acceptedDocCount={acceptedDocCount}
          evidenceCount={evidenceCount}
          pulseScore={pulseScore}
          safeVerifiedFactCount={safeVerifiedFactCount}
          qualityStatus={report?.quality_status}
          isLive={isLive}
        />

        {/* Sector grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-2xl font-semibold text-gray-950">Explore Markets</h2>
              <p className="text-sm text-gray-500 mt-1">
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
                onClick={s.isLive ? () => navigate('/workspace') : undefined}
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
