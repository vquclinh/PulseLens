// Top navigation — primary site sections only. Workspace views live inside /workspace.
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Home', to: '/', exact: true },
  { label: 'Intelligence Workspace', to: '/workspace', workspace: true, hasDropdown: true },
  { label: 'Chat', to: '/chat', exact: true },
] as const

const MARKETS = [
  { name: 'US AI Hardware / Semiconductor', status: 'live', path: '/workspace' },
  { name: 'Cloud GPU Infra', status: 'coming_soon' },
  { name: 'EV Supply Chain', status: 'coming_soon' },
  { name: 'Cybersecurity', status: 'coming_soon' },
  { name: 'Biotech / Pharma', status: 'coming_soon' },
  { name: 'Vietnam E-commerce', status: 'coming_soon' },
]

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const isWorkspace = location.pathname === '/workspace' || location.pathname.startsWith('/workspace/')

  const isActive = (link: typeof NAV_LINKS[number]) => {
    if ('workspace' in link && link.workspace) return isWorkspace
    if ('exact' in link && link.exact) return location.pathname === link.to
    return location.pathname.startsWith(link.to)
  }

  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0, opacity: 0 })
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const navContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const updateIndicator = () => {
      const activeIndex = NAV_LINKS.findIndex(isActive)
      if (activeIndex >= 0 && navContainerRef.current) {
        const activeEl = navContainerRef.current.children[activeIndex] as HTMLElement
        setIndicatorStyle({
          left: activeEl.offsetLeft,
          width: activeEl.offsetWidth,
          opacity: 1
        })
      } else {
        setIndicatorStyle(prev => ({ ...prev, opacity: 0 }))
      }
    }

    // Run once initially, and again slightly later to handle any font loading shifts
    updateIndicator()
    const timer = setTimeout(updateIndicator, 100)
    
    window.addEventListener('resize', updateIndicator)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', updateIndicator)
    }
  }, [location.pathname])

  return (
    <nav className="h-[72px] bg-white border-b border-gray-200 sticky top-0 z-50 flex items-center px-8 gap-8">

      {/* Logo */}
      <Link to="/" className="shrink-0 mr-2">
        <span className="font-logo text-[32px] text-gray-950">
          Pulse<span className="text-blue-600">Lens</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="relative flex items-center gap-6 h-full" ref={navContainerRef}>
        {NAV_LINKS.map(link => {
          const active = isActive(link)
          const hasDropdown = 'hasDropdown' in link && link.hasDropdown

          return (
            <div
              key={link.label}
              className="relative h-full flex items-center"
              onMouseEnter={hasDropdown ? () => setDropdownOpen(true) : undefined}
              onMouseLeave={hasDropdown ? () => setDropdownOpen(false) : undefined}
            >
              <Link
                to={link.to}
                className={[
                  'flex items-center h-full px-2 text-base font-semibold transition-colors whitespace-nowrap',
                  active
                    ? 'text-blue-600'
                    : 'text-gray-600 hover:text-gray-950',
                ].join(' ')}
              >
                {link.label}
                {hasDropdown && (
                  <svg className={`w-4 h-4 ml-1 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </Link>
              
              {hasDropdown && dropdownOpen && (
                <div className="absolute top-full left-0 w-72 bg-white border border-gray-200 rounded-xl shadow-lg py-2 z-50">
                  <div className="px-4 py-2 text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-100 mb-2">
                    Markets
                  </div>
                  {MARKETS.map(m => {
                    const isLive = m.status === 'live'
                    return (
                      <button
                        key={m.name}
                        onClick={isLive && m.path ? () => navigate(m.path) : undefined}
                        className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors text-left ${isLive ? 'hover:bg-gray-50 text-gray-900 cursor-pointer' : 'text-gray-400 cursor-default'}`}
                      >
                        <span className="font-medium">{m.name}</span>
                        {isLive ? (
                          <span className="text-[10px] uppercase font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Live</span>
                        ) : (
                          <span className="text-[10px] uppercase font-bold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">Coming soon</span>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
        {/* Sliding underline */}
        <div 
          className="absolute bottom-[-1px] h-[2px] bg-blue-600 transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)]"
          style={{ left: indicatorStyle.left, width: indicatorStyle.width, opacity: indicatorStyle.opacity }}
        />
      </div>

      {/* Demo badge */}
      <span className="ml-auto shrink-0 text-xs font-semibold text-red-500 bg-red-50 border border-red-200 rounded-full px-3 py-1">
        Demo Web
      </span>

    </nav>
  )
}
