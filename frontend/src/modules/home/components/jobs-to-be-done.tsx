export default function JobsToBeDone() {
  const jobs = [
    'Track market shifts before they become obvious',
    'Compare companies using source-backed evidence',
    'Inspect pricing pressure and supplier risk',
    'Validate AI-generated insights with exact evidence quotes',
    'Ask a grounded analyst assistant about the latest report',
  ]

  return (
    <div className="py-16 bg-slate-50 border-t border-gray-200">
      <div className="max-w-4xl mx-auto px-6">
        <h2 className="font-logo text-3xl font-bold text-gray-950 mb-8 text-center">What you can accomplish</h2>
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
          <ul className="space-y-4">
            {jobs.map((job, idx) => (
              <li key={idx} className="flex items-start gap-4">
                <div className="shrink-0 w-6 h-6 rounded-full bg-green-100 flex items-center justify-center border border-green-200 mt-0.5">
                  <svg className="w-3.5 h-3.5 text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-lg text-gray-800 font-medium">{job}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
