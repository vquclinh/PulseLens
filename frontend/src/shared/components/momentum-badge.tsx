// Company momentum badge — strong_positive through elevated_risk with semantic colors
import type { FC } from 'react'
import type { MomentumLabel } from '@/types/api'
import Badge from './badge'

interface MomentumBadgeProps {
  momentum: MomentumLabel
}

const MomentumBadge: FC<MomentumBadgeProps> = ({ momentum }) => {
  const variantMap: Record<MomentumLabel, 'success' | 'info' | 'default' | 'warning' | 'danger'> = {
    strong_positive: 'success',
    positive: 'success',
    neutral: 'default',
    mixed: 'warning',
    negative: 'danger',
    elevated_risk: 'danger',
  }

  return <Badge variant={variantMap[momentum]}>{momentum.replace(/_/g, ' ')}</Badge>
}

export default MomentumBadge
