/** Multi-period chart component displaying 6 charts in a grid */
import { useMultiPeriodChartData } from '../../hooks'
import { ChartPeriod } from '../../api'
import { CHART_PERIODS } from '../../utils/constants'
import {
  checkDataSufficiency,
  calculatePriceReturn,
  calculateRegressionReturn,
} from '../../utils/chartUtils'
import { Loading } from '../common'
import { PriceChart } from './PriceChart'
import { ChartOverlay } from './ChartOverlay'
import styles from './MultiPeriodChart.module.css'
import overlayStyles from './ChartOverlay.module.css'

interface MultiPeriodChartProps {
  code: string
  periods?: ChartPeriod[]
}

export function MultiPeriodChart({
  code,
  periods: propsPeriods,
}: MultiPeriodChartProps) {
  const { data, isLoading, error, periods } = useMultiPeriodChartData(
    code,
    propsPeriods
  )

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
        {periods.map((period) => {
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

          const formatReturn = (value: number | null): string => {
            if (value === null) return '-'
            const sign = value >= 0 ? '+' : ''
            return `${sign}${value.toFixed(1)}%`
          }

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
                <div className={overlayStyles.chartWrapper}>
                  <PriceChart
                    data={chartData.data}
                    height={200}
                    period={period}
                  />
                  {!sufficiency.isSufficient && (
                    <ChartOverlay
                      actualPeriodLabel={sufficiency.actualPeriodLabel}
                    />
                  )}
                </div>
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
