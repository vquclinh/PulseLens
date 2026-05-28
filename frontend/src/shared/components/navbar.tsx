// Top navigation — primary site sections only. Workspace views live inside /workspace.
import { Link, useLocation, useNavigate } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Home', to: '/', exact: true },
  { label: 'Intelligence Workspace', to: '/workspace', workspace: true },
  { label: 'Chat', to: '/chat', exact: true },
] as const

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const isWorkspace = location.pathname === '/workspace' || location.pathname.startsWith('/workspace/')

  const isActive = (link: typeof NAV_LINKS[number]) => {
    if ('workspace' in link && link.workspace) return isWorkspace
    if ('exact' in link && link.exact) return location.pathname === link.to
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

      {/* Right — workspace CTA */}
      <div className="ml-auto shrink-0">
        <button
          onClick={() => navigate('/workspace')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {isWorkspace ? 'View latest report' : 'Open Workspace →'}
        </button>
      </div>

    </nav>
  )
}
