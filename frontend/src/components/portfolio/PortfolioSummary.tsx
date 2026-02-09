/** Portfolio summary component */
import { PortfolioSummary as PortfolioSummaryType } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './PortfolioSummary.module.css'

interface PortfolioSummaryProps {
  summary: PortfolioSummaryType
}

export function PortfolioSummary({ summary }: PortfolioSummaryProps) {
  const unrealizedPnlClass =
    summary.total_unrealized_pnl >= 0 ? styles.positive : styles.negative
  const unrealizedPnlSign = summary.total_unrealized_pnl >= 0 ? '+' : ''

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <span className={styles.label}>総資産額</span>
        <span className={styles.value}>
          {formatPrice(summary.total_asset)}
        </span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>評価額</span>
        <span className={styles.value}>{formatPrice(summary.total_value)}</span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>評価損益</span>
        <span className={`${styles.value} ${unrealizedPnlClass}`}>
          {unrealizedPnlSign}
          {formatPrice(summary.total_unrealized_pnl)}
        </span>
        <span className={`${styles.subValue} ${unrealizedPnlClass}`}>
          {unrealizedPnlSign}
          {summary.total_unrealized_pnl_percent.toFixed(2)}%
        </span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>現金残高</span>
        <span className={styles.value}>
          {formatPrice(summary.cash_balance)}
        </span>
      </div>
    </div>
  )
}
