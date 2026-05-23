// Source tier badge — Tier 1/2/3/4 with color-coded credibility styling
import type { FC } from 'react'
import Badge from './badge'

interface TierBadgeProps {
  tier: 1 | 2 | 3 | 4
}

const TierBadge: FC<TierBadgeProps> = ({ tier }) => {
  const variantMap = {
    1: 'info',
    2: 'info',
    3: 'success',
    4: 'default',
  } as const

  return <Badge variant={variantMap[tier]}>Tier {tier}</Badge>
}

export default TierBadge
