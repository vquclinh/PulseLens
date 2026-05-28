import { useNavigate } from 'react-router-dom'

export default function Hero() {
  const navigate = useNavigate()

  return (
    <div className="bg-white border-b border-gray-200 py-16 px-6">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <div className="max-w-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 uppercase tracking-wide">
              US AI Hardware · Live
            </span>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 leading-tight">
            AI Hardware Market Intelligence
          </h1>
          <p className="text-lg text-gray-500 leading-relaxed">
            Grounded signals, not AI summaries — every claim traces back to a source.
            67 verified facts from 23 sources, triangulated and scored.
          </p>
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => navigate('/dashboard/us-ai-hardware')}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              Open Dashboard →
            </button>
            <a
              href="#how-it-works"
              className="px-5 py-2.5 border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              How It Works ↓
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
