/** Compare table component for comparing multiple ETFs */
import { ETFDetail } from '../../api'
import { formatPrice, formatPercent, formatAssets } from '../../utils'
import { TagBadge } from '../etf'
import styles from './CompareTable.module.css'

interface CompareTableProps {
  etfs: ETFDetail[]
  onRemove: (code: string) => void
  highlightBest?: boolean
}

type MetricKey = 'dividend_yield' | 'expense_ratio' | 'total_assets'

export function CompareTable({
  etfs,
  onRemove,
  highlightBest = true,
}: CompareTableProps) {
  const findBest = (key: MetricKey, higher: boolean = true): string | null => {
    if (!highlightBest || etfs.length < 2) return null

    const valid = etfs.filter((e) => e[key] !== null)
    if (valid.length === 0) return null

    const best = valid.reduce((a, b) => {
      const aVal = a[key] as number
      const bVal = b[key] as number
      return higher ? (aVal > bVal ? a : b) : aVal < bVal ? a : b
    })

    return best.code
  }

  const bestDividend = findBest('dividend_yield', true)
  const bestExpense = findBest('expense_ratio', false)
  const bestAssets = findBest('total_assets', true)

  const isBest = (code: string, bestCode: string | null): boolean => {
    return bestCode === code
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>項目</th>
            {etfs.map((etf) => (
              <th key={etf.code}>
                <div className={styles.etfHeader}>
                  <span className={styles.code}>{etf.code}</span>
                  <span className={styles.name}>{etf.name}</span>
                  <button
                    className={styles.removeBtn}
                    onClick={() => onRemove(etf.code)}
                    aria-label={`${etf.code}を削除`}
                  >
                    &times;
                  </button>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>カテゴリ</td>
            {etfs.map((etf) => (
              <td key={etf.code}>{etf.category?.name || '-'}</td>
            ))}
          </tr>
          <tr>
            <td>市場価格</td>
            {etfs.map((etf) => (
              <td key={etf.code}>{formatPrice(etf.market_price)}</td>
            ))}
          </tr>
          <tr>
            <td>配当利回り</td>
            {etfs.map((etf) => (
              <td
                key={etf.code}
                className={isBest(etf.code, bestDividend) ? styles.best : ''}
              >
                <span
                  className={
                    isBest(etf.code, bestDividend) ? styles.highlight : ''
                  }
                >
                  {formatPercent(etf.dividend_yield)}
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td>信託報酬</td>
            {etfs.map((etf) => (
              <td
                key={etf.code}
                className={isBest(etf.code, bestExpense) ? styles.best : ''}
              >
                <span
                  className={
                    isBest(etf.code, bestExpense) ? styles.highlight : ''
                  }
                >
                  {formatPercent(etf.expense_ratio)}
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td>純資産総額</td>
            {etfs.map((etf) => (
              <td
                key={etf.code}
                className={isBest(etf.code, bestAssets) ? styles.best : ''}
              >
                <span
                  className={
                    isBest(etf.code, bestAssets) ? styles.highlight : ''
                  }
                >
                  {formatAssets(etf.total_assets)}
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td>タグ</td>
            {etfs.map((etf) => (
              <td key={etf.code}>
                <div className={styles.tags}>
                  {etf.tags.map((tag) => (
                    <TagBadge key={tag.id} tag={tag} size="sm" />
                  ))}
                </div>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
