import { Link, useLocation } from 'react-router-dom'

const WORKSPACE_LINKS = [
  { label: 'Overview', to: '/workspace' },
  { label: 'Evidence', to: '/workspace/evidence' },
  { label: 'Pricing', to: '/workspace/pricing' },
  { label: 'Signals', to: '/workspace/signals' },
  { label: 'Companies', to: '/workspace/companies' },
  { label: 'Pipeline', to: '/workspace/pipeline' },
] as const

function isActivePath(pathname: string, to: string): boolean {
  if (to === '/workspace') return pathname === '/workspace'
  return pathname === to || pathname.startsWith(`${to}/`)
}

export default function WorkspaceNav() {
  const { pathname } = useLocation()

  return (
    <div className="overflow-x-auto border-b border-gray-200">
      <nav className="flex min-w-max gap-2 px-1 py-1" aria-label="Workspace views">
        {WORKSPACE_LINKS.map((link) => {
          const active = isActivePath(pathname, link.to)
          return (
            <Link
              key={link.to}
              to={link.to}
              className={[
                'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
                active
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-950',
              ].join(' ')}
            >
              {link.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
