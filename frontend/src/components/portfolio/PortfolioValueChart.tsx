/** Portfolio value chart component */
import { useCallback, useMemo, useState } from 'react'
import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Scatter,
  ResponsiveContainer,
} from 'recharts'
import { Trade, ValuationHistoryPeriod } from '../../api/types'
import { usePortfolioHistory } from '../../hooks/usePortfolioHistory'
import { useTrades } from '../../hooks/useTrades'
import { formatPrice } from '../../utils'
import { mergeTradesWithChartData } from '../../utils/tradeMarkerUtils'
import { BuyMarkerShape, SellMarkerShape } from './TradeMarker'
import { TradePopover } from './TradePopover'
import styles from './PortfolioValueChart.module.css'

const PERIODS: { value: ValuationHistoryPeriod; label: string }[] = [
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '3y', label: '3Y' },
  { value: '5y', label: '5Y' },
  { value: '10y', label: '10Y' },
  { value: '20y', label: '20Y' },
]

interface PopoverState {
  trades: Trade[]
  date: string
  position: { x: number; y: number }
}

export function PortfolioValueChart() {
  const { data, isLoading, error, period, setPeriod } = usePortfolioHistory()
  const { trades } = useTrades()
  const [popover, setPopover] = useState<PopoverState | null>(null)

  const mergedData = useMemo(
    () => mergeTradesWithChartData(data, trades),
    [data, trades]
  )

  const handleMarkerClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (entry: any) => {
      if (!entry?.payload?.trades) return
      setPopover({
        trades: entry.payload.trades,
        date: entry.payload.date,
        position: {
          x: Math.round(entry.cx ?? 0),
          y: Math.round((entry.cy ?? 0) + 16),
        },
      })
    },
    []
  )

  const handlePopoverClose = useCallback(() => {
    setPopover(null)
  }, [])

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>読み込み中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error}</div>
      </div>
    )
  }

  if (data.length === 0) {
    return null
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>総資産額推移</h3>
        <div className={styles.periodSelector}>
          {PERIODS.map((p) => (
            <button
              key={p.value}
              className={`${styles.periodBtn} ${period === p.value ? styles.active : ''}`}
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.chartWrapper}>
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
              domain={['auto', 'auto']}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'buyMarker' || name === 'sellMarker') return null
                return [formatPrice(value), '総資産額']
              }}
              labelFormatter={(label) => label}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.2}
              strokeWidth={2}
              dot={false}
            />
            <Scatter
              dataKey="buyMarker"
              fill="#10b981"
              shape={<BuyMarkerShape />}
              onClick={handleMarkerClick}
              legendType="none"
            />
            <Scatter
              dataKey="sellMarker"
              fill="#ef4444"
              shape={<SellMarkerShape />}
              onClick={handleMarkerClick}
              legendType="none"
            />
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
    </div>
  )
}

export default PortfolioValueChart
