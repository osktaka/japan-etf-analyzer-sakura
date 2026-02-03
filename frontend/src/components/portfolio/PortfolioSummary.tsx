/** Portfolio summary component */
import { PortfolioSummary as PortfolioSummaryType } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './PortfolioSummary.module.css'

interface PortfolioSummaryProps {
  summary: PortfolioSummaryType
}

export function PortfolioSummary({ summary }: PortfolioSummaryProps) {
  const pnlClass =
    summary.total_unrealized_pnl >= 0 ? styles.positive : styles.negative
  const pnlSign = summary.total_unrealized_pnl >= 0 ? '+' : ''

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <span className={styles.label}>総投資額</span>
        <span className={styles.value}>{formatPrice(summary.total_cost)}</span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>総評価額</span>
        <span className={styles.value}>{formatPrice(summary.total_value)}</span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>評価損益</span>
        <span className={`${styles.value} ${pnlClass}`}>
          {pnlSign}
          {formatPrice(summary.total_unrealized_pnl)}
        </span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>損益率</span>
        <span className={`${styles.value} ${pnlClass}`}>
          {pnlSign}
          {summary.total_unrealized_pnl_percent.toFixed(2)}%
        </span>
      </div>
    </div>
  )
}
