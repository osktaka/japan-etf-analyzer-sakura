/** Holdings list component */
import { Holding } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './HoldingsList.module.css'

interface HoldingsListProps {
  holdings: Holding[]
  isLoading: boolean
  error: string | null
  onETFClick?: (code: string) => void
}

export function HoldingsList({
  holdings,
  isLoading,
  error,
  onETFClick,
}: HoldingsListProps) {
  if (isLoading) {
    return <div className={styles.loading}>読み込み中...</div>
  }

  if (error) {
    return <div className={styles.error}>{error}</div>
  }

  if (holdings.length === 0) {
    return (
      <div className={styles.empty}>
        <p>保有銘柄がありません</p>
        <p className={styles.hint}>取引を登録すると保有銘柄が表示されます</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>銘柄</th>
            <th className={styles.right}>数量</th>
            <th className={styles.right}>平均取得単価</th>
            <th className={styles.right}>現在価格</th>
            <th className={styles.right}>評価額</th>
            <th className={styles.right}>評価損益</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => {
            const pnlClass =
              holding.unrealized_pnl >= 0 ? styles.positive : styles.negative
            const pnlSign = holding.unrealized_pnl >= 0 ? '+' : ''

            return (
              <tr key={holding.etf_code}>
                <td>
                  <button
                    className={styles.etfBtn}
                    onClick={() => onETFClick?.(holding.etf_code)}
                    type="button"
                  >
                    <span className={styles.code}>{holding.etf_code}</span>
                    <span className={styles.name}>
                      {holding.etf?.name || '-'}
                    </span>
                  </button>
                </td>
                <td className={styles.right}>{holding.quantity}口</td>
                <td className={styles.right}>
                  {formatPrice(holding.average_cost)}
                </td>
                <td className={styles.right}>
                  {formatPrice(holding.current_price)}
                </td>
                <td className={styles.right}>
                  {formatPrice(holding.current_value)}
                </td>
                <td className={`${styles.right} ${pnlClass}`}>
                  <div className={styles.pnl}>
                    <span>
                      {pnlSign}
                      {formatPrice(holding.unrealized_pnl)}
                    </span>
                    <span className={styles.pnlPercent}>
                      ({pnlSign}
                      {holding.unrealized_pnl_percent.toFixed(2)}%)
                    </span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
