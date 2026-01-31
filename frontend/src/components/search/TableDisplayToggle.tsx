/** Table display mode toggle component */
import styles from './ETFTableView.module.css'

export type DisplayMode = 'score' | 'trend'

interface TableDisplayToggleProps {
  displayMode: DisplayMode
  onChange: (mode: DisplayMode) => void
}

export function TableDisplayToggle({
  displayMode,
  onChange,
}: TableDisplayToggleProps) {
  return (
    <div className={styles.viewModeToggle}>
      <button
        className={`${styles.periodButton} ${displayMode === 'score' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('score')}
        type="button"
      >
        銘柄スコア
      </button>
      <button
        className={`${styles.periodButton} ${displayMode === 'trend' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('trend')}
        type="button"
      >
        株価傾向
      </button>
    </div>
  )
}
