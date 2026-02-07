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
import { MomentumBadge } from '../common'
import type { ReturnType } from './ReturnTypeToggle'
import type {
  CommonColumnVisibility,
  ScoreColumnVisibility,
} from './ColumnVisibilitySelector'
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
  evaluation_score: 'evaluation_score',
  score_balance: 'score_balance',
  score_dividend: 'score_dividend',
  score_low_cost: 'score_low_cost',
  score_stability: 'score_stability',
  score_volume: 'score_volume',
  score_growth: 'score_growth',
  axis_dividend_power: 'axis_dividend_power',
  axis_cost_efficiency: 'axis_cost_efficiency',
  axis_scale_reliability: 'axis_scale_reliability',
  axis_trading_quality: 'axis_trading_quality',
  axis_return_performance: 'axis_return_performance',
}

const PERIOD_YEARS: Record<PerformancePeriod, number> = {
  '1m': 1 / 12,
  '3m': 0.25,
  '6m': 0.5,
  '1y': 1,
  '3y': 3,
  '5y': 5,
  '10y': 10,
  '20y': 20,
}

type AxisKey =
  | 'evaluation_score'
  | 'axis_dividend_power'
  | 'axis_cost_efficiency'
  | 'axis_scale_reliability'
  | 'axis_trading_quality'
  | 'axis_return_performance'

const AXIS_LABELS: Record<AxisKey, string> = {
  evaluation_score: '評価スコア',
  axis_dividend_power: '配当力',
  axis_cost_efficiency: 'コスト',
  axis_scale_reliability: '安定性',
  axis_trading_quality: '取引規模',
  axis_return_performance: 'リターン',
}

type SortKey = keyof typeof SORT_FIELD_MAP | 'category' | 'price'
type SortDirection = 'asc' | 'desc'

export type PerspectiveKey =
  | 'balance'
  | 'dividend'
  | 'low-cost'
  | 'stability'
  | 'volume'
  | 'growth'
  | 'custom'

interface ETFTableViewProps {
  items: ETFSummary[]
  performance: BatchPerformanceData
  scores?: BatchScoreData
  displayMode?: 'score' | 'trend'
  selectedPeriods: PerformancePeriod[]
  selectedPerspective?: PerspectiveKey
  returnType?: ReturnType
  annualized?: boolean
  commonColumnVisibility?: CommonColumnVisibility
  scoreColumnVisibility?: ScoreColumnVisibility
  momentumVisible?: boolean
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
  selectedPerspective = 'balance',
  returnType = 'price',
  annualized = false,
  commonColumnVisibility,
  scoreColumnVisibility,
  momentumVisible,
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
    // score_* フィールドは evaluation_score 列にマッピング
    if (sortField.startsWith('score_')) return 'evaluation_score'
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

    // evaluation_score の場合、選択中の切り口に対応する score_* フィールドに変換
    let finalApiField = apiField
    if (apiField === 'evaluation_score' && selectedPerspective) {
      const perspectiveToField: Record<PerspectiveKey, SortField> = {
        balance: 'score_balance',
        dividend: 'score_dividend',
        'low-cost': 'score_low_cost',
        stability: 'score_stability',
        volume: 'score_volume',
        growth: 'score_growth',
        custom: 'score_custom',
      }
      finalApiField = perspectiveToField[selectedPerspective]
    }

    let newDirection: SortOrder
    if (currentSortKey === key) {
      // Toggle direction
      newDirection = currentSortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      // New column: determine default direction
      // Desc (higher is better): performance, dividend, price, scores, evaluation_score, axis_*
      // Asc (lower is better): expense_ratio
      // Asc (alphabetical): code, name
      const isPerformanceSort = finalApiField.startsWith('return_')
      const isScoreSort = finalApiField.startsWith('score_')
      const isAxisSort = finalApiField.startsWith('axis_')
      const isEvaluationSort = finalApiField === 'evaluation_score'
      const isDescSort =
        isPerformanceSort ||
        isScoreSort ||
        isAxisSort ||
        isEvaluationSort ||
        finalApiField === 'dividend_yield' ||
        finalApiField === 'price'
      const isAscSort = finalApiField === 'expense_ratio'
      newDirection = isDescSort ? 'desc' : isAscSort ? 'asc' : 'asc'
    }
    onSortChange(finalApiField, newDirection)
  }

  const renderSortIcon = (key: SortKey) => {
    if (currentSortKey !== key) return null
    return currentSortDirection === 'asc' ? ' \u25B2' : ' \u25BC'
  }

  const annualizeReturn = (
    value: number | null | undefined,
    period: PerformancePeriod
  ): number | null | undefined => {
    if (value === null || value === undefined) return value
    const years = PERIOD_YEARS[period]
    if (years === 1) return value
    return value / years
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

  // scoreColumnVisibilityでフィルタされた5軸キー（evaluation_scoreは常に含む）
  const SCORE_VISIBILITY_MAP: Record<string, keyof NonNullable<typeof scoreColumnVisibility>> = {
    axis_dividend_power: 'dividendPower',
    axis_cost_efficiency: 'costEfficiency',
    axis_scale_reliability: 'scaleReliability',
    axis_trading_quality: 'tradingQuality',
    axis_return_performance: 'returnPerformance',
  }

  const allAxisKeys: AxisKey[] = [
    'evaluation_score',
    'axis_dividend_power',
    'axis_cost_efficiency',
    'axis_scale_reliability',
    'axis_trading_quality',
    'axis_return_performance',
  ]

  const axisKeys = allAxisKeys.filter((key) => {
    if (key === 'evaluation_score') return true
    const visKey = SCORE_VISIBILITY_MAP[key]
    return !scoreColumnVisibility || !visKey || scoreColumnVisibility[visKey]
  })

  // Get evaluation score value based on selected perspective
  const getEvaluationScore = (code: string): number | null | undefined => {
    // カスタムの場合はitemsから直接scoreを取得
    if (selectedPerspective === 'custom') {
      const item = items.find((i) => i.code === code)
      return item?.score
    }
    const scoreData = scores?.[code]
    if (!scoreData) return undefined
    return scoreData[selectedPerspective]
  }

  // Get axis score value
  const getAxisScore = (
    code: string,
    axisKey: AxisKey
  ): number | null | undefined => {
    const scoreData = scores?.[code]
    if (!scoreData) return undefined

    if (axisKey === 'evaluation_score') {
      return getEvaluationScore(code)
    }

    const axisScores = scoreData.axis_scores
    if (!axisScores) return undefined

    // Map axisKey to axis_scores field
    const axisMap: Record<string, keyof typeof axisScores> = {
      axis_dividend_power: 'dividend_power',
      axis_cost_efficiency: 'cost_efficiency',
      axis_scale_reliability: 'scale_reliability',
      axis_trading_quality: 'trading_quality',
      axis_return_performance: 'return_performance',
    }

    const field = axisMap[axisKey]
    return field ? axisScores[field] : undefined
  }

  // 表示中のデータ列数を算出して銘柄名の動的max-widthを決定
  const visibleDataColumns =
    ((!commonColumnVisibility || commonColumnVisibility.price) ? 1 : 0) +
    ((!commonColumnVisibility || commonColumnVisibility.dividendYield) ? 1 : 0) +
    ((!commonColumnVisibility || commonColumnVisibility.expenseRatio) ? 1 : 0) +
    ((momentumVisible === undefined || momentumVisible) ? 1 : 0) +
    (displayMode === 'trend' ? selectedPeriods.length : axisKeys.length)

  const nameMaxWidth =
    visibleDataColumns <= 3 ? 600 :
    visibleDataColumns <= 5 ? 450 :
    visibleDataColumns <= 7 ? 320 : 200

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
                style={{ maxWidth: nameMaxWidth }}
              >
                銘柄名{renderSortIcon('name')}
              </th>
              <th
                onClick={() => handleSort('category')}
                className={styles.sortable}
              >
                カテゴリ{renderSortIcon('category')}
              </th>
              {(!commonColumnVisibility || commonColumnVisibility.price) && (
                <th
                  onClick={() => handleSort('price')}
                  className={`${styles.sortable} ${styles.numeric}`}
                >
                  株価{renderSortIcon('price')}
                </th>
              )}
              {(!commonColumnVisibility || commonColumnVisibility.dividendYield) && (
                <th
                  onClick={() => handleSort('dividend')}
                  className={`${styles.sortable} ${styles.numeric}`}
                >
                  配当利回り{renderSortIcon('dividend')}
                </th>
              )}
              {(!commonColumnVisibility || commonColumnVisibility.expenseRatio) && (
                <th
                  onClick={() => handleSort('expense')}
                  className={`${styles.sortable} ${styles.numeric}`}
                >
                  信託報酬{renderSortIcon('expense')}
                </th>
              )}
              {(momentumVisible === undefined || momentumVisible) && (
                <th className={styles.numeric}>勢い</th>
              )}
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
                axisKeys.map((axisKey) => (
                  <th
                    key={axisKey}
                    onClick={() => handleSort(axisKey)}
                    className={`${styles.sortable} ${styles.numeric}`}
                  >
                    {AXIS_LABELS[axisKey]}
                    {renderSortIcon(axisKey)}
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
                <td className={styles.name} title={etf.name} style={{ maxWidth: nameMaxWidth }}>
                  {etf.name}
                </td>
                <td className={styles.category}>{etf.category || '-'}</td>
                {(!commonColumnVisibility || commonColumnVisibility.price) && (
                  <td className={styles.numeric}>
                    {etf.market_price
                      ? `\u00A5${etf.market_price.toLocaleString()}`
                      : '-'}
                  </td>
                )}
                {(!commonColumnVisibility || commonColumnVisibility.dividendYield) && (
                  <td className={styles.numeric}>
                    {etf.dividend_yield
                      ? `${etf.dividend_yield.toFixed(2)}%`
                      : '-'}
                  </td>
                )}
                {(!commonColumnVisibility || commonColumnVisibility.expenseRatio) && (
                  <td className={styles.numeric}>
                    {etf.expense_ratio ? `${etf.expense_ratio.toFixed(2)}%` : '-'}
                  </td>
                )}
                {(momentumVisible === undefined || momentumVisible) && (
                  <td className={styles.numeric}>
                    {etf.momentum_label ? (
                      <MomentumBadge label={etf.momentum_label} />
                    ) : '-'}
                  </td>
                )}
                {displayMode === 'trend' &&
                  selectedPeriods.map((period) => {
                    const returnsData = getReturnsData(etf.code)
                    const rawValue = returnsData[period]
                    const displayValue = annualized
                      ? annualizeReturn(rawValue, period)
                      : rawValue
                    return (
                      <td
                        key={period}
                        className={`${styles.numeric} ${getPerformanceClass(displayValue)}`}
                      >
                        {formatPerformance(displayValue)}
                      </td>
                    )
                  })}
                {displayMode === 'score' &&
                  axisKeys.map((axisKey) => {
                    const scoreValue = getAxisScore(etf.code, axisKey)
                    return (
                      <td
                        key={axisKey}
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
