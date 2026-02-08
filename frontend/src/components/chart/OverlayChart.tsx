/** Overlay comparison chart component */
import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { ChartData } from '../../api'
import {
  normalizeToPercentChange,
  getChartColor,
  calculateNormalizedRegressionLine,
} from '../../utils'
import styles from './OverlayChart.module.css'

interface OverlayChartProps {
  datasets: Array<{
    code: string
    name: string
    data: ChartData
  }>
  height?: number
  showRegressionLine?: boolean
}

interface MergedDataPoint {
  date: string
  [key: string]: string | number
}

export function OverlayChart({
  datasets,
  height = 400,
  showRegressionLine = true,
}: OverlayChartProps) {
  // Normalize each dataset and merge by date
  const { normalizedDatasets, mergedData } = useMemo(() => {
    if (datasets.length === 0) {
      return { normalizedDatasets: [], mergedData: [] }
    }

    const normalized = datasets.map((ds) => ({
      code: ds.code,
      name: ds.name,
      data: normalizeToPercentChange(ds.data.data),
    }))

    // Create merged data structure with all ETFs' values aligned by date
    const dateMap = new Map<string, MergedDataPoint>()

    normalized.forEach((ds) => {
      ds.data.forEach((point) => {
        if (!dateMap.has(point.date)) {
          dateMap.set(point.date, { date: point.date })
        }
        const entry = dateMap.get(point.date)!
        entry[ds.code] = point.percentChange
      })
    })

    // Sort by date and convert to array
    const merged = Array.from(dateMap.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    )

    return { normalizedDatasets: normalized, mergedData: merged }
  }, [datasets])

  // Calculate regression lines for each dataset
  const regressionSegments = useMemo(() => {
    if (!showRegressionLine || mergedData.length < 2) return []

    return normalizedDatasets
      .map((ds, index) => {
        const regression = calculateNormalizedRegressionLine(ds.data)
        if (!regression || ds.data.length < 2) return null

        return {
          code: ds.code,
          color: getChartColor(index),
          segment: [
            { x: ds.data[0].date, y: regression.startY },
            { x: ds.data[ds.data.length - 1].date, y: regression.endY },
          ],
        }
      })
      .filter(Boolean) as Array<{
      code: string
      color: string
      segment: Array<{ x: string; y: number }>
    }>
  }, [normalizedDatasets, showRegressionLine, mergedData.length])

  if (datasets.length === 0 || mergedData.length === 0) {
    return (
      <div className={styles.empty}>
        <p>チャートデータがありません</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.chartArea} style={{ height }}>
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
                const maxWidth = 24
                let truncatedName = ''
                if (ds) {
                  let width = 0
                  for (const ch of ds.name) {
                    width += ch.charCodeAt(0) > 0x7f ? 2 : 1
                    if (width > maxWidth) { truncatedName += '…'; break }
                    truncatedName += ch
                  }
                }
                const label = ds ? `${ds.code} ${truncatedName}` : name
                return [`${value.toFixed(2)}%`, label]
              }}
              labelFormatter={(label) => label}
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
            {regressionSegments.map((rs) => (
              <ReferenceLine
                key={`regression-${rs.code}`}
                segment={rs.segment}
                stroke={rs.color}
                strokeWidth={1}
                strokeDasharray="5 5"
                strokeOpacity={0.6}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className={styles.legendArea}>
        {datasets.map((ds, index) => (
          <div key={ds.code} className={styles.legendItem}>
            <span
              className={styles.legendMarker}
              style={{ backgroundColor: getChartColor(index) }}
            />
            <span className={styles.legendLabel}>
              {ds.code} {ds.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
