// Contradiction alerts — one alert box per conflicting signal pair with both sides shown
import type { FC } from 'react'
import type { ContradictionFlag } from '@/types/api'

interface ContradictionAlertsProps {
  contradictions: ContradictionFlag[]
}

const ContradictionAlerts: FC<ContradictionAlertsProps> = () => {
  return <div />
}

export default ContradictionAlerts
