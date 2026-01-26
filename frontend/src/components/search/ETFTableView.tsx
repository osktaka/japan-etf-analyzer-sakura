/** ETF Table view component */
import { useState, useMemo } from 'react'
import {
  ETFSummary,
  PerformancePeriod,
  PerformanceReturns,
} from '../../api/types'
import styles from './ETFTableView.module.css'

type SortKey =
  | 'code'
  | 'name'
  | 'category'
  | 'price'
  | 'dividend'
  | 'expense'
  | PerformancePeriod
type SortDirection = 'asc' | 'desc'

interface ETFTableViewProps {
  items: ETFSummary[]
  performance: Record<string, PerformanceReturns>
  selectedPeriods: PerformancePeriod[]
  onETFClick: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  isFavorite?: (code: string) => boolean
  onFavoriteToggle?: (code: string) => void
}

export function ETFTableView({
  items,
  performance,
  selectedPeriods,
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
}: ETFTableViewProps) {
  const [sortKey, setSortKey] = useState<SortKey>('code')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let aVal: number | string | null = null
      let bVal: number | string | null = null

      switch (sortKey) {
        case 'code':
          aVal = a.code
          bVal = b.code
          break
        case 'name':
          aVal = a.name
          bVal = b.name
          break
        case 'category':
          aVal = a.category || ''
          bVal = b.category || ''
          break
        case 'price':
          aVal = a.market_price
          bVal = b.market_price
          break
        case 'dividend':
          aVal = a.dividend_yield
          bVal = b.dividend_yield
          break
        case 'expense':
          aVal = a.expense_ratio
          bVal = b.expense_ratio
          break
        default:
          // Performance periods
          aVal = performance[a.code]?.[sortKey as PerformancePeriod] ?? null
          bVal = performance[b.code]?.[sortKey as PerformancePeriod] ?? null
      }

      if (aVal === null && bVal === null) return 0
      if (aVal === null) return 1
      if (bVal === null) return -1

      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      return sortDirection === 'asc' ? cmp : -cmp
    })
  }, [items, performance, sortKey, sortDirection])

  const renderSortIcon = (key: SortKey) => {
    if (sortKey !== key) return null
    return sortDirection === 'asc' ? ' \u25B2' : ' \u25BC'
  }

  const formatPerformance = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    const formatted = value.toFixed(1)
    return value >= 0 ? `+${formatted}%` : `${formatted}%`
  }

  const getPerformanceClass = (value: number | null | undefined) => {
    if (value === null || value === undefined) return ''
    return value >= 0 ? styles.positive : styles.negative
  }

  return (
    <div className={styles.container}>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th
                onClick={() => handleSort('code')}
                className={styles.sortable}
              >
                コード{renderSortIcon('code')}
              </th>
              <th
                onClick={() => handleSort('name')}
                className={styles.sortable}
              >
                銘柄名{renderSortIcon('name')}
              </th>
              <th
                onClick={() => handleSort('category')}
                className={styles.sortable}
              >
                カテゴリ{renderSortIcon('category')}
              </th>
              <th
                onClick={() => handleSort('price')}
                className={`${styles.sortable} ${styles.numeric}`}
              >
                株価{renderSortIcon('price')}
              </th>
              <th
                onClick={() => handleSort('dividend')}
                className={`${styles.sortable} ${styles.numeric}`}
              >
                配当利回り{renderSortIcon('dividend')}
              </th>
              <th
                onClick={() => handleSort('expense')}
                className={`${styles.sortable} ${styles.numeric}`}
              >
                信託報酬{renderSortIcon('expense')}
              </th>
              {selectedPeriods.map((period) => (
                <th
                  key={period}
                  onClick={() => handleSort(period)}
                  className={`${styles.sortable} ${styles.numeric}`}
                >
                  {period.toUpperCase()}
                  {renderSortIcon(period)}
                </th>
              ))}
              {(onCompareToggle || onFavoriteToggle) && (
                <th className={styles.actions}>操作</th>
              )}
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((etf) => (
              <tr
                key={etf.code}
                onClick={() => onETFClick(etf.code)}
                className={styles.row}
              >
                <td className={styles.code}>{etf.code}</td>
                <td className={styles.name}>{etf.name}</td>
                <td className={styles.category}>{etf.category || '-'}</td>
                <td className={styles.numeric}>
                  {etf.market_price
                    ? `\u00A5${etf.market_price.toLocaleString()}`
                    : '-'}
                </td>
                <td className={styles.numeric}>
                  {etf.dividend_yield
                    ? `${etf.dividend_yield.toFixed(2)}%`
                    : '-'}
                </td>
                <td className={styles.numeric}>
                  {etf.expense_ratio ? `${etf.expense_ratio.toFixed(2)}%` : '-'}
                </td>
                {selectedPeriods.map((period) => (
                  <td
                    key={period}
                    className={`${styles.numeric} ${getPerformanceClass(performance[etf.code]?.[period])}`}
                  >
                    {formatPerformance(performance[etf.code]?.[period])}
                  </td>
                ))}
                {(onCompareToggle || onFavoriteToggle) && (
                  <td
                    className={styles.actions}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {onCompareToggle && (
                      <button
                        className={`${styles.actionBtn} ${isInCompare?.(etf.code) ? styles.active : ''}`}
                        onClick={() => onCompareToggle(etf.code)}
                        title="比較"
                      >
                        比較
                      </button>
                    )}
                    {onFavoriteToggle && (
                      <button
                        className={`${styles.actionBtn} ${isFavorite?.(etf.code) ? styles.active : ''}`}
                        onClick={() => onFavoriteToggle(etf.code)}
                        title="お気に入り"
                      >
                        お気に入り
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
