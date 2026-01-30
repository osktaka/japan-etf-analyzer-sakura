/** Holdings list component */
import { useState, useMemo, useCallback } from 'react'
import { Holding } from '../../api/types'
import { formatPrice } from '../../utils'
import { CompareCheckbox } from '../actions/CompareCheckbox'
import styles from './HoldingsList.module.css'

type SortKey =
  | 'etf_code'
  | 'quantity'
  | 'average_cost'
  | 'current_price'
  | 'current_value'
  | 'unrealized_pnl'
type SortOrder = 'asc' | 'desc'

interface HoldingsListProps {
  holdings: Holding[]
  isLoading: boolean
  error: string | null
  onETFClick?: (code: string) => void
  onHistoryClick?: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
}

export function HoldingsList({
  holdings,
  isLoading,
  error,
  onETFClick,
  onHistoryClick,
  isInCompare,
  onCompareToggle,
}: HoldingsListProps) {
  const [sortKey, setSortKey] = useState<SortKey>('current_value')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSortClick = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortKey(key)
        setSortOrder('desc')
      }
    },
    [sortKey]
  )

  const getSortIndicator = (key: SortKey): string => {
    if (sortKey !== key) return ''
    return sortOrder === 'asc' ? ' ▲' : ' ▼'
  }

  const sortedHoldings = useMemo(() => {
    const sorted = [...holdings]
    sorted.sort((a, b) => {
      let aVal: string | number
      let bVal: string | number

      switch (sortKey) {
        case 'etf_code':
          aVal = a.etf_code
          bVal = b.etf_code
          break
        case 'quantity':
          aVal = a.quantity
          bVal = b.quantity
          break
        case 'average_cost':
          aVal = a.average_cost
          bVal = b.average_cost
          break
        case 'current_price':
          aVal = a.current_price
          bVal = b.current_price
          break
        case 'current_value':
          aVal = a.current_value
          bVal = b.current_value
          break
        case 'unrealized_pnl':
          aVal = a.unrealized_pnl
          bVal = b.unrealized_pnl
          break
        default:
          return 0
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
      }

      return 0
    })
    return sorted
  }, [holdings, sortKey, sortOrder])

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
            <th
              onClick={() => handleSortClick('etf_code')}
              style={{ cursor: 'pointer' }}
            >
              銘柄{getSortIndicator('etf_code')}
            </th>
            <th
              className={styles.right}
              onClick={() => handleSortClick('quantity')}
              style={{ cursor: 'pointer' }}
            >
              数量{getSortIndicator('quantity')}
            </th>
            <th
              className={styles.right}
              onClick={() => handleSortClick('average_cost')}
              style={{ cursor: 'pointer' }}
            >
              平均取得単価{getSortIndicator('average_cost')}
            </th>
            <th
              className={styles.right}
              onClick={() => handleSortClick('current_price')}
              style={{ cursor: 'pointer' }}
            >
              現在価格{getSortIndicator('current_price')}
            </th>
            <th
              className={styles.right}
              onClick={() => handleSortClick('current_value')}
              style={{ cursor: 'pointer' }}
            >
              評価額{getSortIndicator('current_value')}
            </th>
            <th
              className={styles.right}
              onClick={() => handleSortClick('unrealized_pnl')}
              style={{ cursor: 'pointer' }}
            >
              評価損益{getSortIndicator('unrealized_pnl')}
            </th>
            {onHistoryClick && <th className={styles.center}>履歴</th>}
            {onCompareToggle && <th className={styles.center}>比較</th>}
          </tr>
        </thead>
        <tbody>
          {sortedHoldings.map((holding) => {
            const pnlClass =
              holding.unrealized_pnl >= 0 ? styles.positive : styles.negative
            const pnlSign = holding.unrealized_pnl >= 0 ? '+' : ''

            return (
              <tr
                key={holding.etf_code}
                onClick={() => onETFClick?.(holding.etf_code)}
                className={styles.row}
              >
                <td>
                  <div className={styles.etfInfo}>
                    <span className={styles.code}>{holding.etf_code}</span>
                    <span className={styles.name}>
                      {holding.etf?.name || '-'}
                    </span>
                  </div>
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
                {onHistoryClick && (
                  <td
                    className={styles.center}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      className={styles.historyBtn}
                      onClick={() => onHistoryClick(holding.etf_code)}
                      type="button"
                      title="取引履歴"
                    >
                      履歴
                    </button>
                  </td>
                )}
                {onCompareToggle && (
                  <td
                    className={styles.center}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <CompareCheckbox
                      isInCompare={isInCompare?.(holding.etf_code) ?? false}
                      onToggle={() => onCompareToggle(holding.etf_code)}
                      size="sm"
                    />
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
