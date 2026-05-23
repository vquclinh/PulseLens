// Generic badge component — small pill with variant colors (default, success, warning, danger)
import type { FC, ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps {
  children: ReactNode
  variant: 'default' | 'success' | 'warning' | 'danger' | 'info'
}

const Badge: FC<BadgeProps> = ({ children, variant }) => {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        variant === 'default' && 'bg-gray-100 text-gray-700',
        variant === 'success' && 'bg-green-100 text-green-700',
        variant === 'warning' && 'bg-amber-100 text-amber-700',
        variant === 'danger' && 'bg-red-100 text-red-700',
        variant === 'info' && 'bg-blue-100 text-blue-700',
      )}
    >
      {children}
    </span>
  )
}

export default Badge
