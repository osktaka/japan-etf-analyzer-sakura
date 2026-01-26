/** View mode toggle component */
import styles from './ETFTableView.module.css'

export type ViewMode = 'card' | 'table'

interface ViewModeToggleProps {
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}

export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
  return (
    <div className={styles.viewModeToggle}>
      <button
        className={`${styles.periodButton} ${mode === 'card' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('card')}
        type="button"
      >
        カード
      </button>
      <button
        className={`${styles.periodButton} ${mode === 'table' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('table')}
        type="button"
      >
        表
      </button>
    </div>
  )
}
