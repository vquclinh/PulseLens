export default function HowItWorks() {
  const steps = [
    {
      number: '01',
      title: 'Collect',
      description: 'Bright Data-powered web access gathers live sources across search, pricing pages, investor pages, and market coverage.',
    },
    {
      number: '02',
      title: 'Extract + Verify',
      description: 'PulseLens converts documents into structured facts tied to exact source quotes. No paraphrasing, no hallucination.',
    },
    {
      number: '03',
      title: 'Score + Synthesize',
      description: 'Signals, company reads, and market briefs are scored and assembled into an analyst-ready workspace.',
    },
    {
      number: '04',
      title: 'Drill down + Ask',
      description: 'Users inspect the evidence manually or ask the grounded assistant for context strictly based on the report.',
    },
  ]

  return (
    <div id="how-it-works" className="py-16 bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-6">
        <div className="mb-10 text-center">
          <h2 className="font-logo text-3xl font-bold text-gray-900">How It Works</h2>
          <p className="text-lg text-gray-600 mt-3">
            Every insight on the platform is traceable to a source document.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map(step => (
            <div key={step.number} className="bg-slate-50 border border-slate-200 rounded-2xl p-6 flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-blue-200 tabular-nums">{step.number}</span>
                <span className="text-lg font-bold text-gray-900">{step.title}</span>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
