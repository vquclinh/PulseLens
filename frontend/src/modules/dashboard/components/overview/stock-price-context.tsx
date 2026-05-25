// Stock price context table — company, current price, 7d%, signal lead time, disclaimer
import type { FC } from 'react'
import { useStock } from '@/hooks/use-stock'

interface StockRowProps {
  ticker: string
}

const StockRow: FC<StockRowProps> = ({ ticker }) => {
  const { data, isLoading } = useStock(ticker)

  if (isLoading) {
    return (
      <tr className="border-t border-gray-100">
        <td className="py-2 px-3 text-xs font-mono font-semibold text-gray-700">{ticker}</td>
        <td colSpan={3} className="py-2 px-3 text-xs text-gray-400">Loading…</td>
      </tr>
    )
  }

  if (!data) return null

  const change = data.price_7d_change_pct
  return (
    <tr className="border-t border-gray-100">
      <td className="py-2 px-3 text-xs font-mono font-semibold text-gray-700">{ticker}</td>
      <td className="py-2 px-3 text-xs tabular-nums text-gray-800">
        {data.price_current != null ? `$${data.price_current.toFixed(2)}` : '—'}
      </td>
      <td className="py-2 px-3 text-xs tabular-nums">
        {change != null ? (
          <span className={change >= 0 ? 'text-green-600' : 'text-red-600'}>
            {change >= 0 ? '+' : ''}{change.toFixed(1)}%
          </span>
        ) : '—'}
      </td>
      <td className="py-2 px-3 text-xs text-gray-500">
        {data.signal_lead_days != null ? `${data.signal_lead_days}d lead` : '—'}
      </td>
    </tr>
  )
}

interface StockPriceContextProps {
  tickers: string[]
}

const StockPriceContext: FC<StockPriceContextProps> = ({ tickers }) => {
  if (!tickers.length) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Stock Price Context</span>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th className="py-1.5 px-3 text-left text-[10px] font-semibold text-gray-400 uppercase">Ticker</th>
              <th className="py-1.5 px-3 text-left text-[10px] font-semibold text-gray-400 uppercase">Price</th>
              <th className="py-1.5 px-3 text-left text-[10px] font-semibold text-gray-400 uppercase">7d %</th>
              <th className="py-1.5 px-3 text-left text-[10px] font-semibold text-gray-400 uppercase">Signal Lead</th>
            </tr>
          </thead>
          <tbody>
            {tickers.map((t) => <StockRow key={t} ticker={t} />)}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-gray-400 border-t border-gray-100 pt-2">
        Data context only — not investment advice. Signal lead = days before price moved.
      </p>
    </div>
  )
}

export default StockPriceContext
