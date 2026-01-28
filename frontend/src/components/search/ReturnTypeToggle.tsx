/** Return type toggle component */
import styles from './ETFTableView.module.css'

export type ReturnType = 'price' | 'regression'

interface ReturnTypeToggleProps {
  returnType: ReturnType
  onChange: (returnType: ReturnType) => void
}

export function ReturnTypeToggle({ returnType, onChange }: ReturnTypeToggleProps) {
  return (
    <div className={styles.viewModeToggle}>
      <button
        className={`${styles.periodButton} ${returnType === 'price' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('price')}
        type="button"
      >
        株価上昇率
      </button>
      <button
        className={`${styles.periodButton} ${returnType === 'regression' ? styles.periodButtonActive : ''}`}
        onClick={() => onChange('regression')}
        type="button"
      >
        回帰上昇率
      </button>
    </div>
  )
}
