import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatScore(n: number): string {
  return n.toFixed(1)
}

export function formatPct(n: number): string {
  const abs = Math.abs(n).toFixed(1)
  return `${n >= 0 ? '+' : '-'}${abs}%`
}

export function formatDate(s: string | null | undefined): string {
  if (!s) return ''
  try {
    return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return s.slice(0, 10)
  }
}

/** Normalize a score from [-1, 1] to [0, 100] for display. */
export function normalizeScore(score: number): number {
  return Math.round(Math.max(0, Math.min(100, (score + 1) / 2 * 100)))
}
