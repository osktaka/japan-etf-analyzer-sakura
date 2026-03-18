/** Holdings chart grid - displays price charts for all held ETFs */
import { useEffect, useMemo, useState } from 'react'
import {
  BatchCodesChartData,
  ChartPeriod,
  Holding,
  Trade,
} from '../../api/types'
import { getETFsChartBatch } from '../../api/etf'
import { tradesApi } from '../../api/trades'
import { demoApi } from '../../api/demo'
import { CHART_PERIODS } from '../../utils/constants'
import {
  calculatePriceReturn,
  calculateRegressionReturn,
  formatReturn,
} from '../../utils/chartUtils'
import { Loading, ErrorMessage } from '../common'
import { PriceChart } from '../chart/PriceChart'
import styles from './HoldingsChartGrid.module.css'

type ChartSize = 'sm' | 'md' | 'lg'

const CHART_HEIGHTS: Record<ChartSize, number> = {
  sm: 150,
  md: 200,
  lg: 300,
}

const SIZE_LABELS: { id: ChartSize; label: string }[] = [
  { id: 'sm', label: '小' },
  { id: 'md', label: '中' },
  { id: 'lg', label: '大' },
]

interface HoldingsChartGridProps {
  holdings: Holding[]
  demoMode?: boolean
  onETFClick?: (code: string) => void
}

export function HoldingsChartGrid({
  holdings,
  demoMode,
  onETFClick,
}: HoldingsChartGridProps) {
  const [period, setPeriod] = useState<ChartPeriod>(() => {
    return (
      (localStorage.getItem('holdings-chart-period') as ChartPeriod) || '1y'
    )
  })
  const [chartSize, setChartSize] = useState<ChartSize>(() => {
    return (localStorage.getItem('holdings-chart-size') as ChartSize) || 'md'
  })
  const [chartData, setChartData] = useState<BatchCodesChartData>({})
  const [trades, setTrades] = useState<Trade[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mountedCount, setMountedCount] = useState(1)

  const codes = useMemo(() => holdings.map((h) => h.etf_code), [holdings])

  // Persist period selection
  useEffect(() => {
    localStorage.setItem('holdings-chart-period', period)
  }, [period])

  // Persist size selection
  useEffect(() => {
    localStorage.setItem('holdings-chart-size', chartSize)
  }, [chartSize])

  // Fetch chart data
  useEffect(() => {
    if (codes.length === 0) return
    setIsLoading(true)
    setError(null)
    setMountedCount(1)
    getETFsChartBatch(codes, period)
      .then(setChartData)
      .catch(() => setError('チャートデータの取得に失敗しました'))
      .finally(() => setIsLoading(false))
  }, [codes, period])

  // Fetch trades
  useEffect(() => {
    if (codes.length === 0) return
    const fetchTrades = demoMode ? demoApi.getTrades() : tradesApi.getAll()
    fetchTrades.then(setTrades).catch(() => setTrades([]))
  }, [codes, demoMode])

  // Progressive rendering
  useEffect(() => {
    if (isLoading) {
      setMountedCount(1)
      return
    }
    if (mountedCount >= codes.length) return
    const timer = setTimeout(() => {
      setMountedCount((prev) => Math.min(prev + 1, codes.length))
    }, 50)
    return () => clearTimeout(timer)
  }, [isLoading, mountedCount, codes.length])

  // Group trades by etf_code
  const tradesMap = useMemo(() => {
    const map: Record<string, Trade[]> = {}
    trades.forEach((t) => {
      if (!map[t.etf_code]) map[t.etf_code] = []
      map[t.etf_code].push(t)
    })
    return map
  }, [trades])

  // Calculate max absolute regression return for border color scaling
  const maxAbsRegReturn = useMemo(() => {
    let max = 0
    holdings.forEach((h) => {
      const d = chartData[h.etf_code]
      if (d && d.data.length > 0) {
        const ret = calculateRegressionReturn(d.data)
        if (ret !== null) max = Math.max(max, Math.abs(ret))
      }
    })
    return max
  }, [holdings, chartData])

  if (holdings.length === 0) return null

  const gridClass =
    chartSize === 'sm'
      ? styles.gridSm
      : chartSize === 'lg'
        ? styles.gridLg
        : styles.gridMd

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>銘柄チャート</span>
        <div className={styles.controls}>
          <div className={styles.btnGroup}>
            {CHART_PERIODS.map((p) => (
              <button
                key={p.id}
                className={`${styles.btn} ${period === p.id ? styles.active : ''}`}
                onClick={() => setPeriod(p.id as ChartPeriod)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className={styles.btnGroup}>
            {SIZE_LABELS.map((s) => (
              <button
                key={s.id}
                className={`${styles.btn} ${chartSize === s.id ? styles.active : ''}`}
                onClick={() => setChartSize(s.id)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading && (
        <div className={styles.loading}>
          <Loading />
        </div>
      )}
      {error && <ErrorMessage message={error} />}
      {!isLoading && !error && (
        <div className={`${styles.grid} ${gridClass}`}>
          {holdings.map((holding, index) => {
            const code = holding.etf_code
            const data = chartData[code]
            const isMounted = index < mountedCount

            const priceReturn =
              data && data.data.length > 0
                ? calculatePriceReturn(data.data)
                : null
            const regressionReturn =
              data && data.data.length > 0
                ? calculateRegressionReturn(data.data)
                : null

            // Border color based on regression return intensity
            const intensity =
              regressionReturn !== null && maxAbsRegReturn > 0
                ? Math.min(Math.abs(regressionReturn) / maxAbsRegReturn, 1)
                : 0
            const borderStyle =
              intensity > 0
                ? {
                    borderColor:
                      regressionReturn! >= 0
                        ? `rgba(34, 197, 94, ${intensity * 0.7 + 0.3})`
                        : `rgba(239, 68, 68, ${intensity * 0.7 + 0.3})`,
                    borderWidth: Math.round(intensity * 2) + 2,
                  }
                : undefined

            return (
              <div
                key={code}
                className={styles.chartCard}
                style={borderStyle}
                onClick={() => onETFClick?.(code)}
              >
                <div className={styles.cardHeader}>
                  <div className={styles.cardHeaderLeft}>
                    <span className={styles.etfCode}>{code}</span>
                    <span className={styles.etfName} title={holding.etf?.name ?? ''}>
                      {holding.etf?.name ?? ''}
                    </span>
                  </div>
                  {priceReturn !== null && (
                    <div className={styles.returnInfo}>
                      <span
                        className={
                          priceReturn >= 0 ? styles.positive : styles.negative
                        }
                      >
                        株価: {formatReturn(priceReturn)}
                      </span>
                      <span className={styles.separator}>/</span>
                      <span
                        className={
                          regressionReturn !== null && regressionReturn >= 0
                            ? styles.positive
                            : styles.negative
                        }
                      >
                        回帰: {formatReturn(regressionReturn)}
                      </span>
                    </div>
                  )}
                </div>
                {data && data.data.length > 0 ? (
                  isMounted ? (
                    <PriceChart
                      data={data.data}
                      height={CHART_HEIGHTS[chartSize]}
                      period={period}
                      showRegressionLine
                      trades={tradesMap[code]}
                    />
                  ) : (
                    <div
                      className={styles.placeholder}
                      style={{ height: CHART_HEIGHTS[chartSize] }}
                    />
                  )
                ) : (
                  <div
                    className={styles.placeholder}
                    style={{ height: CHART_HEIGHTS[chartSize] }}
                  />
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
