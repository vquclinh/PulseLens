// Typed fetch wrapper for all PulseLens API endpoints — report, chat, stock, run
import type { MarketPulseReport, ChatRequest, ChatResponse, StockContext } from '@/types/api'

export async function fetchReport(_id: string): Promise<MarketPulseReport> {
  return undefined as unknown as MarketPulseReport
}

export async function runPipeline(_market: string): Promise<{ report_id: string }> {
  return undefined as unknown as { report_id: string }
}

export async function sendChatMessage(_req: ChatRequest): Promise<ChatResponse> {
  return undefined as unknown as ChatResponse
}

export async function fetchStock(_ticker: string): Promise<StockContext> {
  return undefined as unknown as StockContext
}
