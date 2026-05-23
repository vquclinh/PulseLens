// Stock price context table — company, current price, 7d%, signal lead time, disclaimer
import type { FC } from 'react'
import type { StockContext } from '@/types/api'
import { useStock } from '@/hooks/use-stock'

interface StockPriceContextProps {
  tickers: string[]
}

const StockPriceContext: FC<StockPriceContextProps> = () => {
  return <div />
}

export default StockPriceContext
