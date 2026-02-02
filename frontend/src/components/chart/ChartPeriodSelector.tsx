/** Chart period selector for modal charts */
import { ChartPeriod } from '../../api/types'
import { CHART_PERIODS } from '../../utils/constants'
import styles from './ChartPeriodSelector.module.css'

const PERIOD_ORDER: ChartPeriod[] = [
  '1m',
  '3m',
  '6m',
  '1y',
  '3y',
  '5y',
  '10y',
  '20y',
]

interface ChartPeriodSelectorProps {
  selectedPeriods: ChartPeriod[]
  onChange: (periods: ChartPeriod[]) => void
}

export function ChartPeriodSelector({
  selectedPeriods,
  onChange,
}: ChartPeriodSelectorProps) {
  const togglePeriod = (period: ChartPeriod) => {
    let newPeriods: ChartPeriod[]
    if (selectedPeriods.includes(period)) {
      // 最低1つは選択必須
      if (selectedPeriods.length > 1) {
        newPeriods = selectedPeriods.filter((p) => p !== period)
      } else {
        return
      }
    } else {
      newPeriods = [...selectedPeriods, period]
    }
    // 期間順にソートして返す
    const sorted = newPeriods.sort(
      (a, b) => PERIOD_ORDER.indexOf(a) - PERIOD_ORDER.indexOf(b)
    )
    onChange(sorted)
  }

  return (
    <div className={styles.periodSelector}>
      <div className={styles.periodButtons}>
        {CHART_PERIODS.map(({ id, label }) => (
          <button
            key={id}
            className={`${styles.periodButton} ${
              selectedPeriods.includes(id as ChartPeriod)
                ? styles.periodButtonActive
                : ''
            }`}
            onClick={() => togglePeriod(id as ChartPeriod)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
