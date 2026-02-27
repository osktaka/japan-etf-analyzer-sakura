/** Multi-period chart component displaying 6 charts in a grid */
import { useEffect, useMemo, useState } from 'react'
import { useMultiPeriodChartData } from '../../hooks'
import { ChartPeriod } from '../../api'
import { Trade } from '../../api/types'
import { CHART_PERIODS } from '../../utils/constants'
import {
  checkDataSufficiency,
  calculatePriceReturn,
  calculateRegressionReturn,
  formatReturn,
} from '../../utils/chartUtils'
import { Loading } from '../common'
import { PriceChart } from './PriceChart'
import { ChartOverlay } from './ChartOverlay'
import styles from './MultiPeriodChart.module.css'
import overlayStyles from './ChartOverlay.module.css'

/** Placeholder height matching chart + header area */
const PLACEHOLDER_HEIGHT = 200

interface MultiPeriodChartProps {
  code: string
  periods?: ChartPeriod[]
  trades?: Trade[]
}

export function MultiPeriodChart({
  code,
  periods: propsPeriods,
  trades,
}: MultiPeriodChartProps) {
  const { data, isLoading, error, periods } = useMultiPeriodChartData(
    code,
    propsPeriods
  )

  // Progressive rendering: mount one chart at a time after data loads
  const [mountedCount, setMountedCount] = useState(1)

  useEffect(() => {
    if (isLoading) {
      setMountedCount(1)
      return
    }

    if (mountedCount >= periods.length) return

    const timer = setTimeout(() => {
      setMountedCount((prev) => Math.min(prev + 1, periods.length))
    }, 50)

    return () => clearTimeout(timer)
  }, [isLoading, mountedCount, periods.length])

  // Memoize computed values per period
  const periodComputations = useMemo(() => {
    return periods.map((period) => {
      const chartData = data[period]
      const dataLength = chartData?.data.length ?? 0
      const sufficiency = checkDataSufficiency(period, dataLength)
      const priceReturn =
        chartData && sufficiency.isSufficient
          ? calculatePriceReturn(chartData.data)
          : null
      const regressionReturn =
        chartData && sufficiency.isSufficient
          ? calculateRegressionReturn(chartData.data)
          : null

      return {
        period,
        chartData,
        dataLength,
        sufficiency,
        priceReturn,
        regressionReturn,
      }
    })
  }, [data, periods])

  // Stabilize data references per period for React.memo
  const periodDataMap = useMemo(() => {
    const map = new Map<ChartPeriod, (typeof data)[ChartPeriod]>()
    periods.forEach((period) => {
      map.set(period, data[period])
    })
    return map
  }, [data, periods])

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Loading />
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.error}>
        <p>チャートデータの取得に失敗しました</p>
      </div>
    )
  }

  const getPeriodLabel = (period: ChartPeriod): string => {
    const found = CHART_PERIODS.find((p) => p.id === period)
    return found?.label ?? period
  }

  return (
    <div className={styles.container}>
      <div className={styles.grid}>
        {periodComputations.map((comp, index) => {
          const {
            period,
            dataLength,
            sufficiency,
            priceReturn,
            regressionReturn,
          } = comp
          const chartData = periodDataMap.get(period)
          const isMounted = index < mountedCount

          return (
            <div key={period} className={styles.chartItem}>
              <div className={styles.header}>
                <div className={styles.periodLabel}>
                  {getPeriodLabel(period)}
                </div>
                {sufficiency.isSufficient && priceReturn !== null && (
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
              {chartData && dataLength > 0 ? (
                isMounted ? (
                  <div className={overlayStyles.chartWrapper}>
                    <PriceChart
                      data={chartData.data}
                      height={PLACEHOLDER_HEIGHT}
                      period={period}
                      trades={trades}
                    />
                    {!sufficiency.isSufficient && (
                      <ChartOverlay
                        actualPeriodLabel={sufficiency.actualPeriodLabel}
                      />
                    )}
                  </div>
                ) : (
                  <div
                    className={styles.placeholder}
                    style={{ height: PLACEHOLDER_HEIGHT }}
                  />
                )
              ) : (
                <div className={styles.error}>
                  <p>データなし</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
