/** Price chart component */
import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { ChartDataPoint, ChartPeriod } from '../../api'
import {
  formatPrice,
  getMovingAveragePeriods,
  calculateMovingAverage,
  MA_COLORS,
} from '../../utils'
import styles from './PriceChart.module.css'

interface PriceChartProps {
  data: ChartDataPoint[]
  height?: number
  period?: ChartPeriod
}

interface ChartDataWithMA extends ChartDataPoint {
  ma5?: number | null
  ma25?: number | null
  ma75?: number | null
  ma200?: number | null
}

export function PriceChart({
  data,
  height = 300,
  period = '1y',
}: PriceChartProps) {
  // Calculate moving average data
  const { chartData, maPeriods } = useMemo(() => {
    const periods = getMovingAveragePeriods(period)
    const maData: Record<number, (number | null)[]> = {}

    periods.forEach((p) => {
      maData[p] = calculateMovingAverage(data, p)
    })

    const enhancedData: ChartDataWithMA[] = data.map((point, index) => ({
      ...point,
      ma5: maData[5]?.[index] ?? undefined,
      ma25: maData[25]?.[index] ?? undefined,
      ma75: maData[75]?.[index] ?? undefined,
      ma200: maData[200]?.[index] ?? undefined,
    }))

    return { chartData: enhancedData, maPeriods: periods }
  }, [data, period])

  if (data.length === 0) {
    return (
      <div className={styles.empty}>
        <p>チャートデータがありません</p>
      </div>
    )
  }

  return (
    <div className={styles.container} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              const date = new Date(value)
              return `${date.getMonth() + 1}/${date.getDate()}`
            }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => formatPrice(value).replace('¥', '')}
            domain={['auto', 'auto']}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                close: '終値',
                ma5: 'MA5',
                ma25: 'MA25',
                ma75: 'MA75',
                ma200: 'MA200',
              }
              return [formatPrice(value), labels[name] || name]
            }}
            labelFormatter={(label) => label}
          />
          <Legend
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                close: '終値',
                ma5: 'MA5',
                ma25: 'MA25',
                ma75: 'MA75',
                ma200: 'MA200',
              }
              return labels[value] || value
            }}
          />
          <Line
            type="monotone"
            dataKey="close"
            name="close"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
          {maPeriods.includes(5) && (
            <Line
              type="monotone"
              dataKey="ma5"
              name="ma5"
              stroke={MA_COLORS[5]}
              strokeWidth={1}
              dot={false}
              connectNulls
            />
          )}
          {maPeriods.includes(25) && (
            <Line
              type="monotone"
              dataKey="ma25"
              name="ma25"
              stroke={MA_COLORS[25]}
              strokeWidth={1}
              dot={false}
              connectNulls
            />
          )}
          {maPeriods.includes(75) && (
            <Line
              type="monotone"
              dataKey="ma75"
              name="ma75"
              stroke={MA_COLORS[75]}
              strokeWidth={1}
              dot={false}
              connectNulls
            />
          )}
          {maPeriods.includes(200) && (
            <Line
              type="monotone"
              dataKey="ma200"
              name="ma200"
              stroke={MA_COLORS[200]}
              strokeWidth={1}
              dot={false}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
