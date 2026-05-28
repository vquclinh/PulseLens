import { useNavigate } from 'react-router-dom'

const MARKETS = [
  { name: 'US AI Hardware / Semiconductor', status: 'live' as const },
  { name: 'Cloud GPU Infra', status: 'coming_soon' as const },
  { name: 'EV Supply Chain', status: 'coming_soon' as const },
  { name: 'Cybersecurity', status: 'coming_soon' as const },
  { name: 'Biotech / Pharma', status: 'coming_soon' as const },
  { name: 'Vietnam E-commerce', status: 'coming_soon' as const },
]

export default function MarketCoverage() {
  const navigate = useNavigate()

  return (
    <div className="py-16 border-t border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="font-logo text-3xl font-bold text-gray-950">Market Coverage</h2>
          <p className="text-gray-600 mt-3 text-lg">
            PulseLens is expanding to track fast-moving, high-stakes markets.
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MARKETS.map(m => {
            const isLive = m.status === 'live'
            return (
              <button
                key={m.name}
                onClick={isLive ? () => navigate('/workspace') : undefined}
                className={[
                  'flex items-center justify-between p-5 rounded-2xl border text-left transition-all',
                  isLive
                    ? 'bg-blue-50 border-blue-200 hover:border-blue-400 hover:shadow-md cursor-pointer group'
                    : 'bg-gray-50 border-gray-200 cursor-default opacity-80',
                ].join(' ')}
              >
                <div>
                  <h3 className={`font-semibold text-base ${isLive ? 'text-blue-900' : 'text-gray-700'}`}>
                    {m.name}
                  </h3>
                  <div className="mt-1">
                    {isLive ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold tracking-wide uppercase bg-blue-100 text-blue-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                        Live
                      </span>
                    ) : (
                      <span className="inline-flex px-2 py-0.5 rounded text-[11px] font-bold tracking-wide uppercase bg-gray-200 text-gray-500">
                        Coming soon
                      </span>
                    )}
                  </div>
                </div>
                {isLive && (
                  <svg className="w-5 h-5 text-blue-400 group-hover:text-blue-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
