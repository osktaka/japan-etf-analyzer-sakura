/** ETF Table view component */
import {
  ETFSummary,
  PerformancePeriod,
  PerformanceReturns,
  BatchPerformanceData,
} from '../../api/types'
import { SortField, SortOrder } from '../../api/etf'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import type { ReturnType } from './ReturnTypeToggle'
import styles from './ETFTableView.module.css'

// Map table column keys to API sort fields
const SORT_FIELD_MAP: Record<string, SortField> = {
  code: 'code',
  name: 'name',
  dividend: 'dividend_yield',
  expense: 'expense_ratio',
  '1m': 'return_1m',
  '3m': 'return_3m',
  '6m': 'return_6m',
  '1y': 'return_1y',
  '3y': 'return_3y',
  '5y': 'return_5y',
  '10y': 'return_10y',
  '20y': 'return_20y',
}

type SortKey = keyof typeof SORT_FIELD_MAP | 'category' | 'price'
type SortDirection = 'asc' | 'desc'

interface ETFTableViewProps {
  items: ETFSummary[]
  performance: BatchPerformanceData
  selectedPeriods: PerformancePeriod[]
  returnType?: ReturnType
  onETFClick: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  isFavorite?: (code: string) => boolean
  onFavoriteToggle?: (code: string) => void
  sortField?: SortField
  sortOrder?: SortOrder
  onSortChange?: (field: SortField, order: SortOrder) => void
}

export function ETFTableView({
  items,
  performance,
  selectedPeriods,
  returnType = 'price',
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
  sortField,
  sortOrder,
  onSortChange,
}: ETFTableViewProps) {
  // Get the appropriate returns data based on returnType
  const getReturnsData = (code: string): PerformanceReturns => {
    const item = performance[code]
    if (!item) return {}
    return returnType === 'regression' ? item.regression : item.returns
  }
  // Derive current sort key from sortField prop
  const getCurrentSortKey = (): SortKey => {
    if (!sortField) return 'code'
    for (const [key, field] of Object.entries(SORT_FIELD_MAP)) {
      if (field === sortField) return key as SortKey
    }
    return 'code'
  }

  const currentSortKey = getCurrentSortKey()
  const currentSortDirection: SortDirection = sortOrder || 'asc'

  const handleSort = (key: SortKey) => {
    // category and price are not sortable via API
    if (key === 'category' || key === 'price') return

    const apiField = SORT_FIELD_MAP[key]
    if (!apiField || !onSortChange) return

    let newDirection: SortOrder
    if (currentSortKey === key) {
      // Toggle direction
      newDirection = currentSortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      // New column: default desc for performance, asc for others
      const isPerformanceSort = apiField.startsWith('return_')
      newDirection = isPerformanceSort ? 'desc' : 'asc'
    }
    onSortChange(apiField, newDirection)
  }

  // Items are already sorted by the API, just use them directly
  const sortedItems = items

  const renderSortIcon = (key: SortKey) => {
    if (currentSortKey !== key) return null
    return currentSortDirection === 'asc' ? ' \u25B2' : ' \u25BC'
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
              {onFavoriteToggle && <th className={styles.favoriteCol}></th>}
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
              {onCompareToggle && <th className={styles.compareCol}>比較</th>}
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((etf) => (
              <tr
                key={etf.code}
                onClick={() => onETFClick(etf.code)}
                className={styles.row}
              >
                {onFavoriteToggle && (
                  <td
                    className={styles.favoriteCol}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <FavoriteButton
                      isFavorite={isFavorite?.(etf.code) ?? false}
                      onClick={() => onFavoriteToggle(etf.code)}
                      size="sm"
                    />
                  </td>
                )}
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
                {selectedPeriods.map((period) => {
                  const returnsData = getReturnsData(etf.code)
                  return (
                    <td
                      key={period}
                      className={`${styles.numeric} ${getPerformanceClass(returnsData[period])}`}
                    >
                      {formatPerformance(returnsData[period])}
                    </td>
                  )
                })}
                {onCompareToggle && (
                  <td
                    className={styles.compareCol}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <CompareCheckbox
                      isInCompare={isInCompare?.(etf.code) ?? false}
                      onToggle={() => onCompareToggle(etf.code)}
                      size="sm"
                    />
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
