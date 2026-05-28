// Top navigation — primary site sections only. Workspace views live inside /workspace.
import { useEffect, useRef, useState } from 'react'
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

  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0, opacity: 0 })
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
          return (
            <Link
              key={link.label}
              to={link.to}
              className={[
                'flex items-center h-full px-2 text-base font-semibold transition-colors whitespace-nowrap',
                active
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-950',
              ].join(' ')}
            >
              {link.label}
            </Link>
          )
        })}
        {/* Sliding underline */}
        <div 
          className="absolute bottom-[-1px] h-[2px] bg-blue-600 transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)]"
          style={{ left: indicatorStyle.left, width: indicatorStyle.width, opacity: indicatorStyle.opacity }}
        />
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
