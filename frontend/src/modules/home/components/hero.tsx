import { useNavigate } from 'react-router-dom'

export default function Hero() {
  const navigate = useNavigate()

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-16 md:py-24">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-12 lg:gap-16 items-center">
        {/* Left Column: Positioning & CTA */}
        <div className="flex flex-col gap-6 text-left">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-blue-600 bg-blue-50 px-3 py-1.5 rounded border border-blue-200 uppercase tracking-wide">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
              </span>
              Live Market Intelligence
            </span>
          </div>
          
          <h1 className="font-logo text-5xl lg:text-6xl font-bold text-gray-950 leading-[1.05] tracking-tight">
            Evidence-Backed<br />Market Intelligence
          </h1>
          
          <p className="text-xl text-gray-600 leading-relaxed max-w-2xl">
            PulseLens turns live web, pricing, investor, supplier, and company signals into market intelligence analysts can verify. Explore the latest report in the Intelligence Workspace, then drill down into facts, sources, companies, signals, pricing pressure, and grounded chat.
          </p>
          
          <div className="flex flex-wrap items-center gap-4 mt-2">
            <button
              onClick={() => navigate('/workspace')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-base font-semibold rounded-lg transition-colors shadow-sm"
            >
              Open Workspace →
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 mt-6 text-sm font-medium text-gray-500">
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Source-backed facts
            </span>
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Bright Data-powered collection
            </span>
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Multi-signal analysis
            </span>
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Grounded analyst chat
            </span>
          </div>
        </div>

        {/* Right Column: Product Preview Card */}
        <div className="bg-gray-950 text-white rounded-2xl p-6 lg:p-8 shadow-2xl border border-gray-800 flex flex-col gap-6 relative overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-[-50%] left-[-10%] w-3/4 h-full bg-blue-900/20 blur-3xl rounded-full" style={{ pointerEvents: 'none' }} />
          
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
            <h3 className="text-lg font-bold text-white tracking-wide">Inside the Intelligence Workspace</h3>
          </div>

          <div className="relative z-10 flex flex-col gap-5">
            <div className="flex gap-3 items-start">
              <div className="w-6 h-6 shrink-0 bg-blue-900/50 rounded-md flex items-center justify-center border border-blue-800">
                <span className="text-[10px] font-bold text-blue-300">01</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-200">Market Read</div>
                <div className="text-sm text-gray-400 mt-0.5">Start from an analyst-ready brief for the active market.</div>
              </div>
            </div>
            
            <div className="flex gap-3 items-start">
              <div className="w-6 h-6 shrink-0 bg-blue-900/50 rounded-md flex items-center justify-center border border-blue-800">
                <span className="text-[10px] font-bold text-blue-300">02</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-200">Evidence Explorer</div>
                <div className="text-sm text-gray-400 mt-0.5">Trace insights back to source-backed facts and quotes.</div>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-6 h-6 shrink-0 bg-blue-900/50 rounded-md flex items-center justify-center border border-blue-800">
                <span className="text-[10px] font-bold text-blue-300">03</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-200">Signal Radar</div>
                <div className="text-sm text-gray-400 mt-0.5">Group market movement by pricing, investor, supplier, product, and sentiment signals.</div>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-6 h-6 shrink-0 bg-blue-900/50 rounded-md flex items-center justify-center border border-blue-800">
                <span className="text-[10px] font-bold text-blue-300">04</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-200">Company Lens</div>
                <div className="text-sm text-gray-400 mt-0.5">Compare company narratives, risks, and evidence side by side.</div>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-6 h-6 shrink-0 bg-blue-900/50 rounded-md flex items-center justify-center border border-blue-800">
                <span className="text-[10px] font-bold text-blue-300">05</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-200">Grounded Chat</div>
                <div className="text-sm text-gray-400 mt-0.5">Ask follow-up questions with report, company, signal, or fact context.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
