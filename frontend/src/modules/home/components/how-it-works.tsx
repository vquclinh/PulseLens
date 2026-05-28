interface HowItWorksProps {
  sourceCount: number
  acceptedDocCount: number
  evidenceCount: number
  pulseScore: number
  safeVerifiedFactCount: number | null
  qualityStatus?: string
  isLive: boolean
}

export default function HowItWorks({
  sourceCount,
  acceptedDocCount,
  evidenceCount,
  pulseScore,
  safeVerifiedFactCount,
  qualityStatus,
  isLive,
}: HowItWorksProps) {
  const qualityLabel = isLive ? (qualityStatus ?? 'PASS') : 'Demo baseline'

  const steps = [
    {
      number: '01',
      title: 'Collect',
      description:
        'Web queries issued across multiple sources. BrightData Browser API retrieves JS-rendered pricing pages. Zero fabricated documents — every URL is real.',
      stat: `${sourceCount} sources · ${acceptedDocCount} accepted docs`,
    },
    {
      number: '02',
      title: 'Extract + Verify',
      description:
        'SAFE verification (arXiv:2403.18802) requires every fact\'s evidence_quote to be a verbatim substring of the source document. No paraphrasing, no hallucination.',
      stat: `${evidenceCount} facts · SAFE verified`,
    },
    {
      number: '03',
      title: 'Score',
      description:
        'FinBERT sentiment scoring and cross-source triangulation turn verified facts into market momentum. Pulse score synthesizes signal types into one market indicator.',
      stat: safeVerifiedFactCount == null
        ? `${pulseScore.toFixed(1)} pulse score · ${qualityLabel}`
        : `${safeVerifiedFactCount} SAFE facts · ${pulseScore.toFixed(1)} pulse score`,
    },
  ]

  return (
    <div id="how-it-works" className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-900">How It Works</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Every number on this page is traceable to a source document.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {steps.map(step => (
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
