/** Price chart component */
import React, { useCallback, useMemo, useState } from 'react'
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Scatter,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { ChartDataPoint, ChartPeriod } from '../../api'
import { Trade } from '../../api/types'
import {
  formatPrice,
  getMovingAveragePeriods,
  calculateMovingAverage,
  calculateRegressionLine,
  calculateYAxisDomain,
  decimateChartData,
  MA_COLORS,
} from '../../utils'
import { mergeTradesWithPriceData } from '../../utils/tradeMarkerUtils'
import { BuyMarkerShape, SellMarkerShape } from '../portfolio/TradeMarker'
import { TradePopover } from '../portfolio/TradePopover'
import styles from './PriceChart.module.css'

interface PriceChartProps {
  data: ChartDataPoint[]
  height?: number
  period?: ChartPeriod
  showRegressionLine?: boolean
  trades?: Trade[]
}

interface ChartDataWithMA extends ChartDataPoint {
  ma5?: number | null
  ma25?: number | null
  ma75?: number | null
  ma200?: number | null
}

export const PriceChart = React.memo(function PriceChart({
  data,
  height = 300,
  period = '1y',
  showRegressionLine = true,
  trades,
}: PriceChartProps) {
  // Calculate moving average data, then decimate for performance
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

    // Apply LTTB decimation for large datasets (>500 points)
    const decimated = decimateChartData(enhancedData, 500, (d) => d.close)

    return { chartData: decimated, maPeriods: periods }
  }, [data, period])

  // Merge trade markers with chart data
  const mergedData = useMemo(() => {
    if (!trades || trades.length === 0) return chartData
    return mergeTradesWithPriceData(chartData, trades)
  }, [chartData, trades])

  // Popover state for trade markers
  const [popover, setPopover] = useState<{
    trades: Trade[]
    date: string
    position: { x: number; y: number; markerY: number }
  } | null>(null)

  const handleMarkerClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (entry: any) => {
      if (!entry?.payload?.trades) return
      setPopover({
        trades: entry.payload.trades,
        date: entry.payload.date,
        position: {
          x: Math.round(entry.cx ?? 0),
          y: Math.round((entry.cy ?? 0) + 20),
          markerY: Math.round(entry.cy ?? 0),
        },
      })
    },
    []
  )

  const handlePopoverClose = useCallback(() => setPopover(null), [])

  // Calculate regression line
  const regressionLine = useMemo(() => {
    if (!showRegressionLine || data.length < 2) return null
    return calculateRegressionLine(data)
  }, [data, showRegressionLine])

  // Get start and end dates for regression line segment
  const regressionSegment = useMemo(() => {
    if (!regressionLine || data.length < 2) return null
    return [
      { x: data[0].date, y: regressionLine.startY },
      { x: data[data.length - 1].date, y: regressionLine.endY },
    ]
  }, [regressionLine, data])

  // Calculate explicit Y-axis domain including regression line endpoints
  const yDomain = useMemo(
    (): [number, number] | undefined =>
      calculateYAxisDomain(chartData, regressionLine),
    [chartData, regressionLine]
  )

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
        <ComposedChart
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
            tickFormatter={(value) => formatPrice(value).replace('¥', '')}
            domain={yDomain ?? ['auto', 'auto']}
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
          {regressionSegment && (
            <ReferenceLine
              segment={regressionSegment}
              stroke="#666"
              strokeWidth={1}
              strokeDasharray="5 5"
              ifOverflow="extendDomain"
            />
          )}
          {trades && trades.length > 0 && (
            <>
              <Scatter
                dataKey="buyMarker"
                fill="#10b981"
                shape={<BuyMarkerShape />}
                onClick={handleMarkerClick}
                legendType="none"
                tooltipType="none"
              />
              <Scatter
                dataKey="sellMarker"
                fill="#ef4444"
                shape={<SellMarkerShape />}
                onClick={handleMarkerClick}
                legendType="none"
                tooltipType="none"
              />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
      {popover && (
        <TradePopover
          trades={popover.trades}
          date={popover.date}
          position={popover.position}
          onClose={handlePopoverClose}
        />
      )}
    </div>
  )
})
