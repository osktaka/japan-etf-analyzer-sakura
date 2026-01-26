/** Period selector for table view */
import { PerformancePeriod } from '../../api/types'
import styles from './ETFTableView.module.css'

const ALL_PERIODS: { id: PerformancePeriod; label: string }[] = [
  { id: '1m', label: '1M' },
  { id: '3m', label: '3M' },
  { id: '6m', label: '6M' },
  { id: '1y', label: '1Y' },
  { id: '3y', label: '3Y' },
  { id: '5y', label: '5Y' },
  { id: '10y', label: '10Y' },
  { id: '20y', label: '20Y' },
]

const PERIOD_ORDER: PerformancePeriod[] = [
  '1m',
  '3m',
  '6m',
  '1y',
  '3y',
  '5y',
  '10y',
  '20y',
]

interface PeriodSelectorProps {
  selectedPeriods: PerformancePeriod[]
  onChange: (periods: PerformancePeriod[]) => void
}

export function PeriodSelector({
  selectedPeriods,
  onChange,
}: PeriodSelectorProps) {
  const togglePeriod = (period: PerformancePeriod) => {
    let newPeriods: PerformancePeriod[]
    if (selectedPeriods.includes(period)) {
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
      <span className={styles.periodLabel}>表示期間:</span>
      <div className={styles.periodButtons}>
        {ALL_PERIODS.map(({ id, label }) => (
          <button
            key={id}
            className={`${styles.periodButton} ${
              selectedPeriods.includes(id) ? styles.periodButtonActive : ''
            }`}
            onClick={() => togglePeriod(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

export { PERIOD_ORDER }
