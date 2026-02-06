/** Annualized toggle component */
import styles from './ETFTableView.module.css'

interface AnnualizedToggleProps {
  annualized: boolean
  onChange: (annualized: boolean) => void
}

export function AnnualizedToggle({
  annualized,
  onChange,
}: AnnualizedToggleProps) {
  return (
    <div className={styles.viewModeToggle}>
      <button
        className={`${styles.periodButton} ${annualized ? styles.periodButtonActive : ''}`}
        onClick={() => onChange(!annualized)}
        type="button"
      >
        年率表示
      </button>
    </div>
  )
}
