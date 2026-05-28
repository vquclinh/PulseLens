const STEPS = [
  {
    number: '01',
    title: 'Collect',
    description:
      '32 web queries issued across 23 sources. BrightData Browser API retrieves JS-rendered pricing pages. Zero fabricated documents — every URL is real.',
    stat: '23 sources · 48 accepted docs',
  },
  {
    number: '02',
    title: 'Extract + Verify',
    description:
      'SAFE verification (arXiv:2403.18802) requires every fact\'s evidence_quote to be a verbatim substring of the source document. No paraphrasing, no hallucination.',
    stat: '67 facts · 0 suspicious claims',
  },
  {
    number: '03',
    title: 'Score',
    description:
      'FinBERT sentiment scoring + cross-source triangulation. 10 claims verified by ≥2 independent sources. Pulse score synthesizes 6 signal types into one market momentum indicator.',
    stat: '10 verified claims · 52.7 pulse score',
  },
]

export default function HowItWorks() {
  return (
    <div id="how-it-works" className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-900">How It Works</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Every number on this page is traceable to a source document.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {STEPS.map(step => (
          <div key={step.number} className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-blue-100 tabular-nums">{step.number}</span>
              <span className="text-sm font-bold text-gray-900">{step.title}</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">{step.description}</p>
            <div className="text-[10px] font-mono text-gray-400 bg-gray-50 px-2 py-1 rounded border border-gray-100 mt-auto">
              {step.stat}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
