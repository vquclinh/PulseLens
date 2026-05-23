// Top navigation — Markets, Dashboard (conditional), News, About tabs + Login button
import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()

  const isDashboard = location.pathname.startsWith('/dashboard/')
  const activeMarket = isDashboard ? location.pathname.split('/')[2] : null

  const navLink = (label: string, to: string) => {
    const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to))
    return (
      <Link
        to={to}
        className={[
          'px-1 py-1 text-base font-medium transition-colors border-b-2',
          isActive
            ? 'text-blue-600 border-blue-600'
            : 'text-gray-600 border-transparent hover:text-gray-950',
        ].join(' ')}
      >
        {label}
      </Link>
    )
  }

  return (
    <nav className="h-[72px] bg-white border-b border-gray-200 sticky top-0 z-50 flex items-center px-8 gap-10">

      {/* Logo */}
      <Link to="/" className="shrink-0 mr-2">
        <span className="font-logo text-[32px] text-gray-950">
          Pulse<span className="text-blue-600">Lens</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-8">
        {navLink('Markets', '/')}

        {isDashboard && (
          <Link
            to={`/dashboard/${activeMarket}`}
            className="px-1 py-1 text-base font-medium text-blue-600 border-b-2 border-blue-600 transition-colors"
          >
            Dashboard
          </Link>
        )}

        {navLink('News', '/news')}
        {navLink('About', '/about')}
      </div>

      {/* Right — Login */}
      <div className="ml-auto flex items-center gap-3">
        <button
          onClick={() => navigate('/dashboard/us-ai-hardware')}
          className="text-base font-medium text-gray-600 hover:text-gray-950 transition-colors"
        >
          Log In
        </button>
        <div className="w-px h-5 bg-gray-200" />
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-base font-semibold rounded-lg transition-colors">
          Get Started
        </button>
      </div>

    </nav>
  )
}
