/** Multi-period chart component displaying 6 charts in a grid */
import { useMultiPeriodChartData } from '../../hooks'
import { ChartPeriod } from '../../api'
import { CHART_PERIODS } from '../../utils/constants'
import { Loading } from '../common'
import { PriceChart } from './PriceChart'
import styles from './MultiPeriodChart.module.css'

interface MultiPeriodChartProps {
  code: string
}

export function MultiPeriodChart({ code }: MultiPeriodChartProps) {
  const { data, isLoading, error, periods } = useMultiPeriodChartData(code)

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
          return (
            <div key={period} className={styles.chartItem}>
              <div className={styles.periodLabel}>{getPeriodLabel(period)}</div>
              {chartData && chartData.data.length > 0 ? (
                <PriceChart data={chartData.data} height={200} period={period} />
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
