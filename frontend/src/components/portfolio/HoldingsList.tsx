/** Holdings list component */
import { useState, useMemo, useCallback, useEffect } from 'react'
import { Holding } from '../../api/types'
import { formatPrice } from '../../utils'
import { MomentumBadge } from '../common'
import { CompareCheckbox } from '../actions/CompareCheckbox'
import { HoldingCard } from './HoldingCard'
import styles from './HoldingsList.module.css'

type ViewMode = 'card' | 'table'
type SortKey =
  | 'etf_code'
  | 'quantity'
  | 'average_cost'
  | 'current_price'
  | 'current_value'
  | 'unrealized_pnl'
  | 'unrealized_pnl_percent'
  | 'holding_days'
  | 'annualized_return'
type SortOrder = 'asc' | 'desc'

const CARD_SORT_KEYS: SortKey[] = [
  'unrealized_pnl',
  'unrealized_pnl_percent',
  'annualized_return',
  'holding_days',
  'current_value',
  'quantity',
  'etf_code',
]

const SORT_LABELS: Record<SortKey, string> = {
  etf_code: '銘柄コード',
  quantity: '数量',
  average_cost: '平均取得単価',
  current_price: '現在価格',
  current_value: '評価額',
  unrealized_pnl: '評価損益',
  unrealized_pnl_percent: '損益率',
  holding_days: '保有期間',
  annualized_return: '年率リターン',
}

const STORAGE_KEY = 'holdings-view-mode'

interface HoldingsListProps {
  holdings: Holding[]
  isLoading: boolean
  error: string | null
  onETFClick?: (code: string) => void
  onHistoryClick?: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  onTradeHistory?: () => void
  onAddTrade?: () => void
}

export function HoldingsList({
  holdings,
  isLoading,
  error,
  onETFClick,
  onHistoryClick,
  isInCompare,
  onCompareToggle,
  onTradeHistory,
  onAddTrade,
}: HoldingsListProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'card' || stored === 'table' ? stored : 'table'
  })
  const [sortKey, setSortKey] = useState<SortKey>('current_value')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, viewMode)
  }, [viewMode])

  const handleViewModeChange = useCallback(
    (mode: ViewMode) => {
      if (mode === 'card' && !CARD_SORT_KEYS.includes(sortKey)) {
        setSortKey('unrealized_pnl')
        setSortOrder('desc')
      }
      setViewMode(mode)
    },
    [sortKey]
  )

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

  const handleSortSelectChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value
      const [key, order] = value.split('-') as [SortKey, SortOrder]
      setSortKey(key)
      setSortOrder(order)
    },
    []
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
        case 'unrealized_pnl_percent':
          aVal = a.unrealized_pnl_percent
          bVal = b.unrealized_pnl_percent
          break
        case 'holding_days':
          aVal = a.holding_days ?? 0
          bVal = b.holding_days ?? 0
          break
        case 'annualized_return':
          aVal = a.annualized_return ?? -Infinity
          bVal = b.annualized_return ?? -Infinity
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
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <div className={styles.viewModeToggle}>
            <button
              type="button"
              className={`${styles.toggleBtn} ${viewMode === 'card' ? styles.toggleBtnActive : ''}`}
              onClick={() => handleViewModeChange('card')}
              aria-label="カード形式で表示"
              title="カード形式"
            >
              カード
            </button>
            <button
              type="button"
              className={`${styles.toggleBtn} ${viewMode === 'table' ? styles.toggleBtnActive : ''}`}
              onClick={() => handleViewModeChange('table')}
              aria-label="表形式で表示"
              title="表形式"
            >
              表
            </button>
          </div>
          {viewMode === 'card' && (
            <select
              className={styles.sortSelect}
              value={`${sortKey}-${sortOrder}`}
              onChange={handleSortSelectChange}
              aria-label="並び替え"
            >
              {CARD_SORT_KEYS.map((key) => (
                <optgroup key={key} label={SORT_LABELS[key]}>
                  <option value={`${key}-desc`}>
                    {SORT_LABELS[key]} (大→小)
                  </option>
                  <option value={`${key}-asc`}>
                    {SORT_LABELS[key]} (小→大)
                  </option>
                </optgroup>
              ))}
            </select>
          )}
        </div>
        {(onTradeHistory || onAddTrade) && (
          <div className={styles.tradeButtons}>
            {onTradeHistory && (
              <button
                type="button"
                className={styles.tradeHistoryBtn}
                onClick={onTradeHistory}
              >
                取引履歴
              </button>
            )}
            {onAddTrade && (
              <button
                type="button"
                className={styles.addTradeBtn}
                onClick={onAddTrade}
              >
                取引を追加
              </button>
            )}
          </div>
        )}
      </div>

      {viewMode === 'table' ? (
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
              <th
                className={styles.right}
                onClick={() => handleSortClick('unrealized_pnl_percent')}
                style={{ cursor: 'pointer' }}
              >
                損益率{getSortIndicator('unrealized_pnl_percent')}
              </th>
              <th
                className={styles.right}
                onClick={() => handleSortClick('holding_days')}
                style={{ cursor: 'pointer' }}
              >
                保有期間{getSortIndicator('holding_days')}
              </th>
              <th
                className={styles.right}
                onClick={() => handleSortClick('annualized_return')}
                style={{ cursor: 'pointer' }}
              >
                年率リターン{getSortIndicator('annualized_return')}
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
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <span className={styles.code}>{holding.etf_code}</span>
                        <MomentumBadge label={holding.etf?.momentum_label} code={holding.etf_code} />
                      </span>
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
                    {pnlSign}
                    {formatPrice(holding.unrealized_pnl)}
                  </td>
                  <td className={`${styles.right} ${pnlClass}`}>
                    {pnlSign}
                    {holding.unrealized_pnl_percent.toFixed(2)}%
                  </td>
                  <td className={styles.right}>
                    {holding.holding_period || '-'}
                  </td>
                  <td
                    className={`${styles.right} ${
                      holding.annualized_return !== null &&
                      holding.annualized_return !== undefined
                        ? holding.annualized_return >= 0
                          ? styles.positive
                          : styles.negative
                        : ''
                    }`}
                  >
                    {holding.annualized_return !== null &&
                    holding.annualized_return !== undefined
                      ? `${holding.annualized_return >= 0 ? '+' : ''}${holding.annualized_return.toFixed(2)}%`
                      : '-'}
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
      ) : (
        <div className={styles.cardGrid}>
          {sortedHoldings.map((holding) => (
            <HoldingCard
              key={holding.etf_code}
              holding={holding}
              onClick={() => onETFClick?.(holding.etf_code)}
              onHistoryClick={
                onHistoryClick
                  ? () => onHistoryClick(holding.etf_code)
                  : undefined
              }
              isInCompare={isInCompare?.(holding.etf_code)}
              onCompareToggle={
                onCompareToggle
                  ? () => onCompareToggle(holding.etf_code)
                  : undefined
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
