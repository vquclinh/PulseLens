// TanStack Query hook for fetching stock context with 4-hour stale time
import { useQuery } from '@tanstack/react-query'
import { fetchStock } from '@/lib/api-client'

export function useStock(ticker: string) {
  return useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => fetchStock(ticker),
    enabled: !!ticker,
    staleTime: 4 * 60 * 60 * 1000,
  })
}
