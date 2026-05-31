import { useState } from 'react'
import type { ReactNode } from 'react'
import Navbar from '@/shared/components/navbar'
import { X } from 'lucide-react'

interface WorkspaceLayoutProps {
  children: ReactNode
  isLoading?: boolean
}

export default function WorkspaceLayout({ children, isLoading = false }: WorkspaceLayoutProps) {
  const [dismissed, setDismissed] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      {children}

      {/* Demo latency notice — visible while loading, auto-hides when done */}
      {isLoading && !dismissed && (
        <div className="fixed bottom-4 right-4 z-50 max-w-[260px] rounded-xl border border-red-300 bg-red-50/90 backdrop-blur-sm px-4 py-3 shadow-lg">
          <div className="flex items-start justify-between gap-2">
            <p className="text-xs leading-relaxed text-red-700">
              <span className="font-semibold block mb-0.5">⚠ Demo deployment</span>
              Backend runs on Render's free tier — first load may take
              20–60 s to wake up. Please wait patiently.
            </p>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              aria-label="Dismiss notice"
              className="shrink-0 mt-0.5 text-red-400 hover:text-red-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
