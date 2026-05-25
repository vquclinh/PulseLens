// Typed fetch wrapper — all PulseLens API endpoints
import type { MarketPulseReport, ChatRequest, ChatResponse, StockContext, FactObject } from '@/types/api'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function _fetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function fetchReport(id: string): Promise<MarketPulseReport> {
  return _fetch(`/api/report/${encodeURIComponent(id)}`)
}

export async function runPipeline(payload: {
  market?: string
  companies?: string[]
  time_window?: string
}): Promise<{ report_id: string; pulse_score: number; pulse_status: string }> {
  return _fetch('/api/run', { method: 'POST', body: JSON.stringify(payload) })
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  return _fetch('/api/chat', { method: 'POST', body: JSON.stringify(req) })
}

export async function fetchStock(ticker: string): Promise<StockContext> {
  return _fetch(`/api/stock/${encodeURIComponent(ticker)}`)
}

export async function fetchReportFacts(reportId: string): Promise<FactObject[]> {
  return _fetch(`/api/report/${encodeURIComponent(reportId)}/facts`)
}

export async function fetchLatestReportId(): Promise<{ report_id: string }> {
  return _fetch('/api/reports/latest')
}
