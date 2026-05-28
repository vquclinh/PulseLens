const SECTIONS = [
  {
    title: 'Live web collection',
    body: "PulseLens uses Bright Data's SERP API, Web Scraper, and Scraping Browser to fetch content from news sources, SEC filings, investor relations pages, job boards, and pricing pages. Each document is assigned a source tier at collection time.",
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
    body: 'Raw documents are processed through OpenRouter using a schema-constrained extraction prompt. Every extracted fact must include a verbatim evidence quote from the source text.',
  },
  {
    title: 'Evidence validation',
    body: 'PulseLens validates evidence quotes, runs SAFE-style atomic verification, applies FinBERT sentiment scoring, and triangulates claims across independent sources before reporting them.',
  },
  {
    title: 'Scoring formula',
    body: 'Pulse Score is a weighted average of signal scores, normalized to 0-100. Confidence is grounded in verified evidence quality and corroboration, not unsupported narrative text.',
  },
]

export default function PipelineAuditPage() {
  return (
    <section className="flex flex-col gap-6">
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Pipeline Audit</p>
        <h2 className="mt-1 text-2xl font-bold text-gray-950">Transparency and methodology</h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-600">
          A compact view of how PulseLens turns live web evidence into report signals. This is the workspace
          replacement for the previous top-level methodology page.
        </p>
      </div>

      {SECTIONS.map((section) => (
        <div key={section.title} className="bg-white border border-gray-200 rounded-xl p-6 flex flex-col gap-3">
          <h3 className="text-base font-semibold text-gray-900">{section.title}</h3>
          {section.body && <p className="text-sm text-gray-600 leading-relaxed">{section.body}</p>}
          {section.rows && (
            <table className="w-full text-sm border-collapse mt-1">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  <th className="pb-2 pr-4">Tier</th>
                  <th className="pb-2 pr-4">Weight</th>
                  <th className="pb-2">Examples</th>
                </tr>
              </thead>
              <tbody>
                {section.rows.map((row) => (
                  <tr key={row.tier} className="border-b border-gray-100 last:border-0">
                    <td className="py-2 pr-4 font-medium text-gray-900">{row.tier}</td>
                    <td className="py-2 pr-4 tabular-nums text-blue-600 font-semibold">{row.weight}</td>
                    <td className="py-2 text-gray-500">{row.examples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </section>
  )
}
