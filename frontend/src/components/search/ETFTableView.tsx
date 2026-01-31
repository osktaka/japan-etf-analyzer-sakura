/** ETF Table view component */
import {
  BatchPerformanceData,
  BatchScoreData,
  ETFSummary,
  PerformancePeriod,
  PerformanceReturns,
} from '../../api/types'
import { SortField, SortOrder } from '../../api/etf'
import { CompareCheckbox } from '../actions'
import { FavoriteButton } from '../favorite'
import type { ReturnType } from './ReturnTypeToggle'
import styles from './ETFTableView.module.css'

// Map table column keys to API sort fields
const SORT_FIELD_MAP: Record<string, SortField> = {
  code: 'code',
  name: 'name',
  price: 'price',
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
  balance: 'score_balance',
  dividend_score: 'score_dividend',
  'low-cost': 'score_low_cost',
  stability: 'score_stability',
  volume: 'score_volume',
  growth: 'score_growth',
}

type ScoreKey =
  | 'balance'
  | 'dividend_score'
  | 'low-cost'
  | 'stability'
  | 'volume'
  | 'growth'

const SCORE_LABELS: Record<ScoreKey, string> = {
  balance: 'バランス',
  dividend_score: '配当収入',
  'low-cost': '低コスト',
  stability: '安定性',
  volume: '取引規模',
  growth: '成長性',
}

type SortKey = keyof typeof SORT_FIELD_MAP | 'category' | 'price'
type SortDirection = 'asc' | 'desc'

interface ETFTableViewProps {
  items: ETFSummary[]
  performance: BatchPerformanceData
  scores?: BatchScoreData
  displayMode?: 'score' | 'trend'
  selectedPeriods: PerformancePeriod[]
  returnType?: ReturnType
  scoringMode?: 'full' | 'partial'
  onScoringModeChange?: (mode: 'full' | 'partial') => void
  onETFClick: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  isFavorite?: (code: string) => boolean
  onFavoriteToggle?: (code: string) => void
  isHolding?: (code: string) => boolean
  sortField?: SortField
  sortOrder?: SortOrder
  onSortChange?: (field: SortField, order: SortOrder) => void
}

export function ETFTableView({
  items,
  performance,
  scores,
  displayMode = 'trend',
  selectedPeriods,
  returnType = 'price',
  scoringMode = 'full',
  onScoringModeChange,
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
  isHolding,
  sortField,
  sortOrder,
  onSortChange,
}: ETFTableViewProps) {
  // Get the appropriate returns data based on returnType
  const getReturnsData = (code: string): PerformanceReturns => {
    const item = performance[code]
    if (!item) return {}
    return (returnType === 'regression' ? item.regression : item.returns) ?? {}
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
    // category is not sortable via API
    if (key === 'category') return

    const apiField = SORT_FIELD_MAP[key]
    if (!apiField || !onSortChange) return

    let newDirection: SortOrder
    if (currentSortKey === key) {
      // Toggle direction
      newDirection = currentSortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      // New column: determine default direction
      // Desc (higher is better): performance, dividend, price, scores
      // Asc (lower is better): expense_ratio
      // Asc (alphabetical): code, name
      const isPerformanceSort = apiField.startsWith('return_')
      const isScoreSort = apiField.startsWith('score_')
      const isDescSort =
        isPerformanceSort ||
        isScoreSort ||
        apiField === 'dividend_yield' ||
        apiField === 'price'
      const isAscSort = apiField === 'expense_ratio'
      newDirection = isDescSort ? 'desc' : isAscSort ? 'asc' : 'asc'
    }
    onSortChange(apiField, newDirection)
  }

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

  const formatScore = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return value.toFixed(1)
  }

  const getScoreClass = (value: number | null | undefined) => {
    if (value === null || value === undefined) return ''
    if (value >= 70) return styles.positive
    if (value >= 50) return ''
    return styles.negative
  }

  const scoreKeys: ScoreKey[] = [
    'balance',
    'dividend_score',
    'low-cost',
    'stability',
    'volume',
    'growth',
  ]

  return (
    <div className={styles.container}>
      {displayMode === 'score' && onScoringModeChange && (
        <div className={styles.scoringModeToggle}>
          <span className={styles.toggleLabel}>スコア計算:</span>
          <button
            className={`${styles.toggleButton} ${scoringMode === 'full' ? styles.active : ''}`}
            onClick={() => onScoringModeChange('full')}
          >
            総合評価
          </button>
          <button
            className={`${styles.toggleButton} ${scoringMode === 'partial' ? styles.active : ''}`}
            onClick={() => onScoringModeChange('partial')}
          >
            軸別評価
          </button>
        </div>
      )}
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
              {displayMode === 'trend' &&
                selectedPeriods.map((period) => (
                  <th
                    key={period}
                    onClick={() => handleSort(period)}
                    className={`${styles.sortable} ${styles.numeric}`}
                  >
                    {period.toUpperCase()}
                    {renderSortIcon(period)}
                  </th>
                ))}
              {displayMode === 'score' &&
                scoreKeys.map((scoreKey) => (
                  <th
                    key={scoreKey}
                    onClick={() => handleSort(scoreKey)}
                    className={`${styles.sortable} ${styles.numeric}`}
                  >
                    {SCORE_LABELS[scoreKey]}
                    {renderSortIcon(scoreKey)}
                  </th>
                ))}
              {onCompareToggle && <th className={styles.compareCol}>比較</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((etf) => (
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
                      isHolding={isHolding?.(etf.code)}
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
                {displayMode === 'trend' &&
                  selectedPeriods.map((period) => {
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
                {displayMode === 'score' &&
                  scoreKeys.map((scoreKey) => {
                    const scoreData = scores?.[etf.code]
                    const actualKey =
                      scoreKey === 'dividend_score' ? 'dividend' : scoreKey
                    const scoreValue =
                      scoreData?.[actualKey as keyof typeof scoreData]
                    return (
                      <td
                        key={scoreKey}
                        className={`${styles.numeric} ${getScoreClass(scoreValue)}`}
                      >
                        {formatScore(scoreValue)}
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
