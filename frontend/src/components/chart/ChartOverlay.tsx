/** Chart overlay component for insufficient data indication */
import styles from './ChartOverlay.module.css'

interface ChartOverlayProps {
  actualPeriodLabel: string
}

export function ChartOverlay({ actualPeriodLabel }: ChartOverlayProps) {
  return (
    <div className={styles.overlay}>
      <div className={styles.message}>
        データ不足
        <div className={styles.subMessage}>（{actualPeriodLabel}のみ）</div>
      </div>
    </div>
  )
}
