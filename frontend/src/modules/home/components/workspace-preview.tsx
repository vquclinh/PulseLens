export default function WorkspacePreview() {
  const modules = [
    { name: 'Overview', desc: 'Market read, status, strongest signal, and summary.' },
    { name: 'Evidence Explorer', desc: 'Search, filter, and open source-backed facts behind every insight.' },
    { name: 'Pricing Intelligence', desc: 'Identify price hikes, discounts, and margin pressure.' },
    { name: 'Company Lens', desc: 'Compare entity momentum, drivers, and recent events.' },
    { name: 'Signal Radar', desc: 'Track market shifts categorized by underlying signal type.' },
    { name: 'Trust / Pipeline', desc: 'Audit the exact queries and parsing that generated the report.' },
    { name: 'Context-aware Chat', desc: 'Ask an analyst assistant strictly grounded in the report evidence.' },
  ]

  return (
    <div className="py-16 bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-[1fr_1.5fr] gap-12 items-center">
        <div>
          <h2 className="font-logo text-3xl font-bold text-gray-950 mb-4">Intelligence Workspace</h2>
          <p className="text-lg text-gray-600 mb-8 leading-relaxed">
            Stop guessing where the data comes from. The Intelligence Workspace breaks down the market into specialized lenses, with every claim tied back to a verfiable source URL.
          </p>
          <button
            onClick={() => window.location.assign('/workspace')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gray-950 text-white rounded-lg font-semibold hover:bg-gray-800 transition-colors"
          >
            Explore the Workspace →
          </button>
        </div>
        
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 shadow-inner">
          <div className="grid sm:grid-cols-2 gap-4">
            {modules.map(mod => (
              <div key={mod.name} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
                <h3 className="font-semibold text-gray-900 text-sm mb-1">{mod.name}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{mod.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
