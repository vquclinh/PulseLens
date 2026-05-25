// About page — methodology, evidence triangulation, source tiering, scoring formula
import Navbar from '@/shared/components/navbar'

const SECTIONS = [
  {
    title: 'How PulseLens collects data',
    body: "PulseLens uses Bright Data's SERP API, Web Scraper, and Scraping Browser to fetch content from news sources, SEC filings, investor relations pages, job boards, and pricing pages. Each document is assigned a source tier at collection time — not after.",
  },
  {
    title: 'Source tiering',
    rows: [
      { tier: 'Tier 1', weight: '1.0', examples: 'SEC EDGAR, IR pages, earnings transcripts' },
      { tier: 'Tier 2', weight: '0.8', examples: 'Reuters, Bloomberg, WSJ, FT' },
      { tier: 'Tier 3', weight: '0.5', examples: 'TechCrunch, Wired, SemiAnalysis, Ars Technica' },
      { tier: 'Tier 4', weight: '0.4', examples: 'LinkedIn jobs, pricing pages, company blogs' },
    ],
  },
  {
    title: 'Structured fact extraction',
    body: 'Raw documents are processed through OpenRouter using the configured Agent 3 model, with a schema-constrained extraction prompt. Every extracted fact must include an exact verbatim quote from the source. Any fact whose evidence_quote cannot be found in the source document is automatically discarded — this eliminates LLM hallucination at the extraction stage.',
  },
  {
    title: 'Evidence triangulation',
    body: 'A claim is only surfaced if it is corroborated by at least 2 independent source domains. A single Tier 1 source overrides this requirement. When conflicting signals are detected (same entity, opposite sentiment), PulseLens does not blend them into a neutral statement — it flags the contradiction explicitly and recommends manual review.',
  },
  {
    title: 'Scoring formula',
    body: 'Pulse Score = weighted average of signal scores, normalised from [−1, 1] to [0, 100]. Signal weights reflect financial impact: Investor Signal (0.25), News Sentiment (0.20), Pricing Pressure (0.18), Strategic Messaging (0.15), Hiring Momentum (0.12), Product Launch (0.07), Supplier Risk (0.03). Contradicted signals receive a 0.5 penalty on their weight. Confidence = mean final_confidence across all verified claims.',
  },
]

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-3xl mx-auto px-6 py-12 flex flex-col gap-10">

        <div>
          <h1 className="text-2xl font-bold text-gray-900">Methodology</h1>
          <p className="text-sm text-gray-500 mt-2 leading-relaxed">
            PulseLens is built for buy-side analysts who need to understand <em>why</em> they should trust the data.
            Every claim traces back to a primary source. Every score is a deterministic function of evidence — not LLM opinion.
          </p>
        </div>

        {SECTIONS.map(s => (
          <div key={s.title} className="bg-white border border-gray-200 rounded-xl p-6 flex flex-col gap-3">
            <h2 className="text-base font-semibold text-gray-900">{s.title}</h2>
            {s.body && <p className="text-sm text-gray-600 leading-relaxed">{s.body}</p>}
            {s.rows && (
              <table className="w-full text-sm border-collapse mt-1">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    <th className="pb-2 pr-4">Tier</th>
                    <th className="pb-2 pr-4">Weight</th>
                    <th className="pb-2">Examples</th>
                  </tr>
                </thead>
                <tbody>
                  {s.rows.map(r => (
                    <tr key={r.tier} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 pr-4 font-medium text-gray-900">{r.tier}</td>
                      <td className="py-2 pr-4 tabular-nums text-blue-600 font-semibold">{r.weight}</td>
                      <td className="py-2 text-gray-500">{r.examples}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}

      </div>
    </div>
  )
}
