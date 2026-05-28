// Top navigation — Home, Dashboard, Evidence, Pricing, Signals, Companies, Pipeline, Chat
import { Link, useLocation, useNavigate } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Home',      to: '/',                          exact: true },
  { label: 'Dashboard', to: '/dashboard/us-ai-hardware',  exact: false, dashboardTab: true },
  { label: 'Evidence',  to: '/dashboard/us-ai-hardware',  exact: false, dashboardOnly: true },
  { label: 'Pricing',   to: '/dashboard/us-ai-hardware',  exact: false, dashboardOnly: true },
  { label: 'Signals',   to: '/dashboard/us-ai-hardware',  exact: false, dashboardOnly: true },
  { label: 'Companies', to: '/dashboard/us-ai-hardware',  exact: false, dashboardOnly: true },
  { label: 'Pipeline',  to: '/about',                     exact: false },
  { label: 'Chat',      to: '/dashboard/us-ai-hardware',  exact: false, dashboardOnly: true },
] as const

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const isDashboard = location.pathname.startsWith('/dashboard/')

  const isActive = (link: typeof NAV_LINKS[number]) => {
    // dashboard-only links highlight only when "Dashboard" tab is active and
    // link is "Dashboard" itself — prevents all 5 dashboard links lighting up
    if ('dashboardOnly' in link && link.dashboardOnly) return false
    if ('dashboardTab' in link && link.dashboardTab) return isDashboard
    if (link.exact) return location.pathname === link.to
    return location.pathname.startsWith(link.to)
  }

  return (
    <nav className="h-[72px] bg-white border-b border-gray-200 sticky top-0 z-50 flex items-center px-8 gap-8">

      {/* Logo */}
      <Link to="/" className="shrink-0 mr-2">
        <span className="font-logo text-[32px] text-gray-950">
          Pulse<span className="text-blue-600">Lens</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-5">
        {NAV_LINKS.map(link => (
          <Link
            key={link.label}
            to={link.to}
            className={[
              'px-1 py-1 text-sm font-medium transition-colors border-b-2 whitespace-nowrap',
              isActive(link)
                ? 'text-blue-600 border-blue-600'
                : 'text-gray-600 border-transparent hover:text-gray-950',
            ].join(' ')}
          >
            {link.label}
          </Link>
        ))}
      </div>

      {/* Right — Open Dashboard CTA */}
      <div className="ml-auto shrink-0">
        <button
          onClick={() => navigate('/dashboard/us-ai-hardware')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          Open Dashboard →
        </button>
      </div>

    </nav>
  )
}
