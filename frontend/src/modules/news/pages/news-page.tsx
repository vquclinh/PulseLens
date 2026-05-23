// Global news feed — all tracked signals across every market, no dashboard required
import Navbar from '@/shared/components/navbar'

export default function NewsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-gray-900">News Feed</h1>
        <p className="text-sm text-gray-500 mt-1">
          All tracked signals across active markets — no dashboard required.
        </p>
        <div className="mt-8 text-sm text-gray-400">
          News feed coming soon — wired to backend in the next phase.
        </div>
      </div>
    </div>
  )
}
