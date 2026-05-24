// API call functions — all model types are imported from ./index
// Do NOT add model/interface definitions here; add them to index.ts instead

import type {
  MarketPulseReport,
  ChatRequest,
  ChatResponse,
  StockContext,
} from './index'

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

export function runPipeline(payload: {
  market?: string
  companies?: string[]
  time_window?: string
}): Promise<{ report_id: string }> {
  return _fetch('/api/run', { method: 'POST', body: JSON.stringify(payload) })
}

export function getReport(reportId: string): Promise<MarketPulseReport> {
  return _fetch(`/api/report/${encodeURIComponent(reportId)}`)
}

export function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return _fetch('/api/chat', { method: 'POST', body: JSON.stringify(request) })
}

export function getStock(ticker: string): Promise<StockContext> {
  return _fetch(`/api/stock/${encodeURIComponent(ticker)}`)
}
