/** Portfolio value chart component */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Scatter,
  Legend,
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
  position: { x: number; y: number; markerY: number }
}

export function PortfolioValueChart() {
  const { data, isLoading, error, period, setPeriod } = usePortfolioHistory()
  const { trades } = useTrades()
  const [popover, setPopover] = useState<PopoverState | null>(null)
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia('(max-width: 640px)').matches
  )
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 640px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

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
          y: Math.round((entry.cy ?? 0) + 20),
          markerY: Math.round(entry.cy ?? 0),
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
        <h3 className={styles.title}>総資産推移</h3>
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
            margin={isMobile ? { top: 5, right: 10, left: 5, bottom: 5 } : { top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: isMobile ? 10 : 12 }}
              minTickGap={isMobile ? 40 : 30}
              tickFormatter={(value) => {
                const date = new Date(value)
                return `${date.getMonth() + 1}/${date.getDate()}`
              }}
            />
            <YAxis
              tick={{ fontSize: isMobile ? 10 : 12 }}
              width={isMobile ? 55 : 65}
              tickFormatter={(value) => formatPrice(value).replace('¥', '')}
              domain={['auto', 'auto']}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const data = payload[0]?.payload
                if (!data) return null
                return (
                  <div className={styles.tooltip}>
                    <p className={styles.tooltipDate}>{label}</p>
                    <p
                      className={styles.tooltipRow}
                      style={{ color: data.unrealized_pnl >= 0 ? '#10b981' : '#ef4444' }}
                    >
                      <span
                        className={styles.legendDot}
                        style={{ background: data.unrealized_pnl >= 0 ? '#10b981' : '#ef4444' }}
                      />
                      評価損益: {data.unrealized_pnl >= 0 ? '+' : ''}{formatPrice(data.unrealized_pnl)}
                    </p>
                    <p className={styles.tooltipRow}>
                      <span className={styles.legendDot} style={{ background: '#38bdf8' }} />
                      取得原価: {formatPrice(data.total_cost)}
                    </p>
                    <p className={styles.tooltipRow}>
                      <span className={styles.legendDot} style={{ background: '#a78bfa' }} />
                      現金残高: {formatPrice(data.cash_balance)}
                    </p>
                    <hr className={styles.tooltipDivider} />
                    <p className={styles.tooltipRow} style={{ fontWeight: 600 }}>
                      総資産: {formatPrice(data.value)}
                    </p>
                  </div>
                )
              }}
            />
            <Legend
              iconSize={isMobile ? 8 : 14}
              wrapperStyle={{ fontSize: isMobile ? '0.625rem' : '0.75rem' }}
              payload={[
                { value: '評価損益', type: 'rect', color: '#059669' },
                { value: '取得原価', type: 'rect', color: '#0ea5e9' },
                { value: '現金残高', type: 'rect', color: '#8b5cf6' },
              ]}
            />
            {/* 現金残高（最下層・紫系）*/}
            <Area
              type="monotone"
              dataKey="cash_balance"
              stackId="1"
              name="現金残高"
              stroke="#8b5cf6"
              fill="#a78bfa"
              fillOpacity={0.5}
              strokeWidth={1}
              dot={false}
            />
            {/* 取得原価（中層・水色系）*/}
            <Area
              type="monotone"
              dataKey="total_cost"
              stackId="1"
              name="取得原価"
              stroke="#0ea5e9"
              fill="#38bdf8"
              fillOpacity={0.45}
              strokeWidth={1}
              dot={false}
            />
            {/* 評価損益（最上層・緑系）*/}
            <Area
              type="monotone"
              dataKey="unrealized_pnl"
              stackId="1"
              name="評価損益"
              stroke="#059669"
              fill="#34d399"
              fillOpacity={0.5}
              strokeWidth={1}
              dot={false}
            />
            <Scatter
              dataKey="buyMarker"
              fill="#10b981"
              shape={<BuyMarkerShape isMobile={isMobile} />}
              onClick={handleMarkerClick}
              legendType="none"
              tooltipType="none"
            />
            <Scatter
              dataKey="sellMarker"
              fill="#ef4444"
              shape={<SellMarkerShape isMobile={isMobile} />}
              onClick={handleMarkerClick}
              legendType="none"
              tooltipType="none"
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
