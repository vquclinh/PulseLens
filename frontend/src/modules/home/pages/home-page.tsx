import Navbar from '@/shared/components/navbar'
import Hero from '../components/hero'
import MarketCoverage from '../components/market-coverage'
import Capabilities from '../components/capabilities'
import WorkspacePreview from '../components/workspace-preview'
import JobsToBeDone from '../components/jobs-to-be-done'
import HowItWorks from '../components/how-it-works'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Navbar />
      
      {/* Hero section */}
      <Hero />
      
      {/* Market coverage area, showing multi-market vision */}
      <MarketCoverage />
      
      {/* Why PulseLens */}
      <Capabilities />
      
      {/* Visual walkthrough of the Workspace */}
      <WorkspacePreview />
      
      {/* Jobs to be done list */}
      <JobsToBeDone />
      
      {/* The simplified process step */}
      <HowItWorks />

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 pt-8 pb-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm text-gray-500 font-medium">
            © 2026 PulseLens · Evidence-backed market intelligence for fast-moving sectors.
          </span>
          <span className="text-sm text-gray-400">
            Data context only — not investment advice
          </span>
        </div>
      </footer>
    </div>
  )
}
