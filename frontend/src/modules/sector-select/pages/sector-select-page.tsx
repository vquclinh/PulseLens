// Homepage — market intelligence landing page with live snapshot, signals, company momentum, and sector grid
import { useNavigate } from 'react-router-dom'
import Navbar from '@/shared/components/navbar'
import SectorCard from '../components/sector-card'

// ── Mock data (replaced by real API data once backend is wired) ──────────────

const PULSE = { score: 78.3, status: 'Heating Up', trend: +6.1, confidence: 0.86 }

const SIGNAL_BREAKDOWN = [
  { label: 'Investor Signal',      score: 88, weight: 0.25, positive: true  },
  { label: 'News Sentiment',       score: 71, weight: 0.20, positive: true  },
  { label: 'Hiring Momentum',      score: 74, weight: 0.12, positive: true  },
  { label: 'Strategic Messaging',  score: 63, weight: 0.15, positive: true  },
  { label: 'Product Launch',       score: 55, weight: 0.07, positive: true  },
  { label: 'Pricing Pressure',     score: 41, weight: 0.18, positive: false },
  { label: 'Supplier Risk',        score: 29, weight: 0.03, positive: false },
]

const COMPANIES = [
  { ticker: 'NVDA', name: 'Nvidia',      momentum: 'strong_positive', score:  82, change: '+8.2%'  },
  { ticker: 'AMD',  name: 'AMD',         momentum: 'positive',        score:  61, change: '+3.1%'  },
  { ticker: 'AVGO', name: 'Broadcom',    momentum: 'positive',        score:  48, change: '+2.4%'  },
  { ticker: 'DELL', name: 'Dell',        momentum: 'positive',        score:  37, change: '+1.8%'  },
  { ticker: 'MU',   name: 'Micron',      momentum: 'positive',        score:  44, change: '+2.9%'  },
  { ticker: 'HPE',  name: 'HPE',         momentum: 'neutral',         score:  12, change: '+0.4%'  },
  { ticker: 'INTC', name: 'Intel',       momentum: 'negative',        score: -24, change: '-4.1%'  },
  { ticker: 'SMCI', name: 'Supermicro',  momentum: 'elevated_risk',   score: -18, change: '-6.3%'  },
]

const RECENT_SIGNALS = [
  {
    id: 'fact_c1',
    tier: 1,
    domain: 'ir.nvidia.com',
    date: 'May 21',
    signal: 'Investor Signal',
    sentiment: 'positive',
    company: 'Nvidia',
    quote: 'Blackwell GB200 NVL72 production ramp confirmed; volume shipments to hyperscalers began Q1 2025.',
    confidence: 0.94,
  },
  {
    id: 'fact_a3',
    tier: 2,
    domain: 'reuters.com',
    date: 'May 20',
    signal: 'Hiring Momentum',
    sentiment: 'positive',
    company: 'Nvidia',
    quote: 'Nvidia job postings for AI infrastructure roles surged 40% week-over-week, the highest pace since Q3 2024.',
    confidence: 0.88,
  },
  {
    id: 'fact_e1',
    tier: 2,
    domain: 'reuters.com',
    date: 'May 21',
    signal: 'Supplier Risk',
    sentiment: 'negative',
    company: 'Supermicro',
    quote: "SMCI's audit committee expects to file the delayed 10-K within 60 days, but two analysts downgraded citing ongoing uncertainty.",
    confidence: 0.71,
  },
  {
    id: 'fact_d4',
    tier: 3,
    domain: 'semianalysis.com',
    date: 'May 19',
    signal: 'Pricing Pressure',
    sentiment: 'neutral',
    company: 'Market',
    quote: 'Cloud GPU on-demand pricing fell 8–12% this week, consistent with post-hyperscaler-buildout supply normalization patterns.',
    confidence: 0.79,
  },
]

const SECTORS = [
  { name: 'US AI Hardware',     description: 'Nvidia, AMD, Intel, Broadcom, Supermicro, Dell, HPE, Micron', isLive: true,  slug: 'us-ai-hardware' },
  { name: 'US Cybersecurity',   description: 'Palo Alto, CrowdStrike, Fortinet, Zscaler',                  isLive: false, slug: '' },
  { name: 'Cloud GPU Infra',    description: 'AWS, Azure, GCP, CoreWeave, Lambda',                         isLive: false, slug: '' },
  { name: 'EV Supply Chain',    description: 'Tesla, BYD, LG Energy, CATL',                               isLive: false, slug: '' },
  { name: 'Vietnam E-commerce', description: 'Shopee, Tiki, Lazada, VinCommerce',                          isLive: false, slug: '' },
  { name: 'Biotech / Pharma',   description: 'Moderna, BioNTech, Vertex, Regeneron',                      isLive: false, slug: '' },
]

// ── Helper components ─────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: number }) {
  const colors: Record<number, string> = {
    1: 'bg-blue-100 text-blue-700 border-blue-200',
    2: 'bg-sky-100 text-sky-700 border-sky-200',
    3: 'bg-teal-100 text-teal-700 border-teal-200',
    4: 'bg-gray-100 text-gray-600 border-gray-200',
  }
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${colors[tier]}`}>
      T{tier}
    </span>
  )
}

function SentimentDot({ sentiment }: { sentiment: string }) {
  const colors: Record<string, string> = {
    positive: 'bg-green-500',
    negative: 'bg-red-500',
    neutral:  'bg-amber-400',
  }
  return <span className={`w-2 h-2 rounded-full inline-block ${colors[sentiment] ?? 'bg-gray-400'}`} />
}

function MomentumChip({ momentum, score }: { momentum: string; score: number }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    strong_positive: { label: 'Strong ↑', cls: 'bg-green-100 text-green-800 border-green-200' },
    positive:        { label: 'Positive ↑', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    neutral:         { label: 'Neutral →', cls: 'bg-gray-100 text-gray-600 border-gray-200' },
    negative:        { label: 'Negative ↓', cls: 'bg-red-50 text-red-700 border-red-200' },
    elevated_risk:   { label: 'Risk ⚠', cls: 'bg-purple-100 text-purple-800 border-purple-200' },
  }
  const { label, cls } = cfg[momentum] ?? cfg.neutral
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${cls}`}>
      {label}
    </span>
  )
}

function PulseStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    'Heating Up':  'bg-green-500',
    'Stable':      'bg-blue-500',
    'Cooling Down':'bg-red-500',
    'Volatile':    'bg-amber-500',
    'Risk Rising': 'bg-purple-500',
  }
  const color = map[status] ?? 'bg-gray-500'
  return (
    <span className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
      <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
      {status}
    </span>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SectorSelectPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Navbar />

      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col gap-10">

        {/* Hero */}
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 leading-tight">
              Market Intelligence Dashboard
            </h1>
            <p className="text-sm text-gray-500 mt-1 max-w-lg">
              Web signals synthesized into grounded intelligence — every claim traces back to a source.
              Updated daily. Currently tracking the <strong className="text-gray-700">US AI Hardware</strong> sector.
            </p>
          </div>
          <button
            onClick={() => navigate('/workspace')}
            className="shrink-0 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            Open Workspace →
          </button>
        </div>

        {/* Market snapshot row */}
        <div className="grid grid-cols-3 gap-4" id="signals">

          {/* Pulse score */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Pulse Score</span>
              <PulseStatusBadge status={PULSE.status} />
            </div>
            <div className="flex items-end gap-3">
              <span className="text-5xl font-bold text-gray-900 leading-none tabular-nums">
                {PULSE.score}
              </span>
              <span className="text-sm text-gray-400 mb-1">/ 100</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded">
                +{PULSE.trend} vs last week
              </span>
              <span className="text-xs text-gray-400">Confidence {(PULSE.confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="text-xs text-gray-400 pt-1 border-t border-gray-100">
              Last 7 days · May 16–23, 2025
            </div>
          </div>

          {/* Signal breakdown */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Signal Breakdown</span>
            <div className="flex flex-col gap-2">
              {SIGNAL_BREAKDOWN.map(s => (
                <div key={s.label} className="flex items-center gap-2">
                  <span className="text-[11px] text-gray-500 w-36 shrink-0 truncate">{s.label}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${s.positive ? 'bg-blue-500' : 'bg-red-400'}`}
                      style={{ width: `${s.score}%` }}
                    />
                  </div>
                  <span className="text-[11px] tabular-nums text-gray-600 w-6 text-right">{s.score}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Company momentum */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Company Momentum</span>
            <div className="flex flex-col gap-1.5">
              {COMPANIES.map(c => (
                <div key={c.ticker} className="flex items-center gap-2">
                  <span className="text-xs font-mono font-semibold text-gray-700 w-10 shrink-0">{c.ticker}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        c.score >= 50  ? 'bg-green-500' :
                        c.score >= 20  ? 'bg-emerald-400' :
                        c.score >= 0   ? 'bg-gray-300' :
                        c.score >= -20 ? 'bg-red-300' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.max(4, (c.score + 100) / 2)}%` }}
                    />
                  </div>
                  <MomentumChip momentum={c.momentum} score={c.score} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent signals */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-900">Recent Signals</h2>
            <button
              onClick={() => navigate('/workspace/evidence')}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              View all {'>'}
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {RECENT_SIGNALS.map(s => (
              <div key={s.id} className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <TierBadge tier={s.tier} />
                  <span className="text-xs text-gray-400">{s.domain}</span>
                  <span className="text-xs text-gray-400">·</span>
                  <span className="text-xs text-gray-400">{s.date}</span>
                  <div className="ml-auto flex items-center gap-1.5">
                    <SentimentDot sentiment={s.sentiment} />
                    <span className="text-[10px] font-medium text-gray-500 uppercase">{s.signal}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed border-l-2 border-gray-200 pl-2.5 italic">
                  "{s.quote}"
                </p>
                <div className="flex items-center gap-2 pt-0.5">
                  <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                    [{s.id}]
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {s.company} · confidence {s.confidence.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sector grid */}
        <div id="about">
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
                onClick={s.isLive ? () => navigate('/workspace') : undefined}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-gray-200 pt-6 pb-2 flex items-center justify-between">
          <span className="text-xs text-gray-400">
            © 2025 PulseLens · Market intelligence for the AI hardware sector
          </span>
          <span className="text-xs text-gray-400">
            Data context only — not investment advice
          </span>
        </footer>

      </div>
    </div>
  )
}
