// TanStack Query hook for fetching and caching the active market report
import { useQuery } from '@tanstack/react-query'
import { fetchReport } from '@/lib/api-client'

export function useReport(reportId: string) {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId),
    enabled: !!reportId,
  })
}
