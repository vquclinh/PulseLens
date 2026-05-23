// Inline SVG sparkline for 7-day pulse score history using Recharts AreaChart
import type { FC } from 'react'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'

interface SparklineProps {
  data: number[]
  color?: string
}

const Sparkline: FC<SparklineProps> = ({ data, color = '#2563eb' }) => {
  const chartData = data.map((v) => ({ v }))
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={chartData}>
        <Area type="monotone" dataKey="v" stroke={color} fill={color} fillOpacity={0.2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default Sparkline
