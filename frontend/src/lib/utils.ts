// Shared utilities — cn() class merger, number formatters, date formatters
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatScore(_n: number): string {
  return ''
}

export function formatPct(_n: number): string {
  return ''
}

export function formatDate(_s: string): string {
  return ''
}
