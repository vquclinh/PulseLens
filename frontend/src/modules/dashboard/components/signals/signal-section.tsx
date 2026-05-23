// Collapsible signal section — header with score bar, narrative, evidence cards, contradiction note
import type { FC } from 'react'
import type { SignalSummary, VerifiedClaim } from '@/types/api'
import EvidenceCard from './evidence-card'

interface SignalSectionProps {
  signal: SignalSummary
  claims: VerifiedClaim[]
}

const SignalSection: FC<SignalSectionProps> = () => {
  return <div />
}

export default SignalSection
