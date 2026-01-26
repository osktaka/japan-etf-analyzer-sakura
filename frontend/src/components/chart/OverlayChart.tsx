/** Overlay comparison chart component */
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
import { ChartData } from '../../api'
import { normalizeToPercentChange, getChartColor } from '../../utils'
import styles from './OverlayChart.module.css'

interface OverlayChartProps {
  datasets: Array<{
    code: string
    name: string
    data: ChartData
  }>
  height?: number
}

interface MergedDataPoint {
  date: string
  [key: string]: string | number
}

export function OverlayChart({ datasets, height = 400 }: OverlayChartProps) {
  if (datasets.length === 0) {
    return (
      <div className={styles.empty}>
        <p>チャートデータがありません</p>
      </div>
    )
  }

  // Normalize each dataset and merge by date
  const normalizedDatasets = datasets.map((ds) => ({
    code: ds.code,
    name: ds.name,
    data: normalizeToPercentChange(ds.data.data),
  }))

  // Create merged data structure with all ETFs' values aligned by date
  const dateMap = new Map<string, MergedDataPoint>()

  normalizedDatasets.forEach((ds) => {
    ds.data.forEach((point) => {
      if (!dateMap.has(point.date)) {
        dateMap.set(point.date, { date: point.date })
      }
      const entry = dateMap.get(point.date)!
      entry[ds.code] = point.percentChange
    })
  })

  // Sort by date and convert to array
  const mergedData = Array.from(dateMap.values()).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  )

  if (mergedData.length === 0) {
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
          data={mergedData}
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
            tickFormatter={(value) => `${value.toFixed(1)}%`}
            domain={['auto', 'auto']}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const ds = datasets.find((d) => d.code === name)
              const label = ds ? `${ds.code} ${ds.name}` : name
              return [`${value.toFixed(2)}%`, label]
            }}
            labelFormatter={(label) => label}
          />
          <Legend
            formatter={(value) => {
              const ds = datasets.find((d) => d.code === value)
              return ds ? `${ds.code} ${ds.name}` : value
            }}
          />
          {normalizedDatasets.map((ds, index) => (
            <Line
              key={ds.code}
              type="monotone"
              dataKey={ds.code}
              stroke={getChartColor(index)}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
