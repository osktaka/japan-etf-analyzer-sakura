/** Chart container with period selector */
import { useState } from 'react'
import { ChartPeriod } from '../../api'
import { useChartData } from '../../hooks'
import { CHART_PERIODS } from '../../utils'
import { Loading, ErrorMessage } from '../common'
import { PriceChart } from './PriceChart'
import styles from './ChartContainer.module.css'

interface ChartContainerProps {
  code: string
}

export function ChartContainer({ code }: ChartContainerProps) {
  const [period, setPeriod] = useState<ChartPeriod>('1y')
  const { data, isLoading, error, refetch } = useChartData(code, period)

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>価格チャート</h3>
        <div className={styles.periods}>
          {CHART_PERIODS.map((p) => (
            <button
              key={p.id}
              className={`${styles.periodBtn} ${period === p.id ? styles.active : ''}`}
              onClick={() => setPeriod(p.id as ChartPeriod)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      {isLoading && <Loading />}
      {error && (
        <ErrorMessage
          message="チャートの取得に失敗しました"
          onRetry={refetch}
        />
      )}
      {data && <PriceChart data={data.data} period={period} />}
    </div>
  )
}
