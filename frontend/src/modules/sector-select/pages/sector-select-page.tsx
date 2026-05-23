// Screen 1 — sector grid: US AI Hardware (live) + 5 coming-soon sectors
import { useNavigate } from 'react-router-dom'
import SectorCard from '../components/sector-card'

export default function SectorSelectPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-3xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">PulseLens</h1>
          <p className="text-sm text-gray-500 mt-1">
            Select a market — one active for this demo, more coming soon.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <SectorCard
            name="US AI Hardware"
            description="Nvidia, AMD, Intel, Broadcom, Supermicro, Dell, HPE, Micron"
            isLive={true}
            onClick={() => navigate('/dashboard/us-ai-hardware')}
          />
          <SectorCard name="US Cybersecurity" description="Coming soon" isLive={false} />
          <SectorCard name="Cloud GPU Infra" description="Coming soon" isLive={false} />
          <SectorCard name="EV Supply Chain" description="Coming soon" isLive={false} />
          <SectorCard name="Vietnam E-commerce" description="Coming soon" isLive={false} />
          <SectorCard name="Biotech / Pharma" description="Coming soon" isLive={false} />
        </div>
      </div>
    </div>
  )
}
