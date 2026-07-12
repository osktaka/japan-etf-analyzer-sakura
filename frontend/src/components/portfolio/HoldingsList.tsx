/** Holdings list component */
import { useState, useMemo, useCallback, useEffect } from 'react'
import { Holding } from '../../api/types'
import { formatPrice } from '../../utils'
import { MomentumBadge } from '../common'
import { CompareCheckbox } from '../actions/CompareCheckbox'
import { HoldingCard } from './HoldingCard'
import styles from './HoldingsList.module.css'

type ViewMode = 'card' | 'table'
type PnlMode = 'current' | 'total'
type SortKey =
  | 'etf_code'
  | 'quantity'
  | 'average_cost'
  | 'current_price'
  | 'current_value'
  | 'unrealized_pnl'
  | 'unrealized_pnl_percent'
  | 'total_pnl'
  | 'total_buy_amount'
  | 'total_sell_amount'
  | 'total_pnl_percent'
  | 'holding_days'
  | 'annualized_return'
type SortOrder = 'asc' | 'desc'

const CARD_SORT_KEYS_CURRENT: SortKey[] = [
  'unrealized_pnl',
  'unrealized_pnl_percent',
  'annualized_return',
  'holding_days',
  'current_value',
  'quantity',
  'etf_code',
]

const CARD_SORT_KEYS_TOTAL: SortKey[] = [
  'total_buy_amount',
  'total_sell_amount',
  'total_pnl_percent',
  'total_pnl',
  'annualized_return',
  'holding_days',
  'quantity',
  'etf_code',
]

const SORT_LABELS: Record<SortKey, string> = {
  etf_code: '銘柄コード',
  quantity: '数量',
  average_cost: '平均取得単価',
  current_price: '現在価格',
  current_value: '現在評価額',
  unrealized_pnl: '評価損益',
  unrealized_pnl_percent: '損益率',
  total_pnl: '総利益',
  total_buy_amount: '累計投資額',
  total_sell_amount: '累計売却額',
  total_pnl_percent: '総利益率',
  holding_days: '保有期間',
  annualized_return: '年率リターン',
}

const STORAGE_KEY = 'holdings-view-mode'
const PNL_MODE_STORAGE_KEY = 'holdings-pnl-mode'
const SORT_KEY_STORAGE_KEY = 'holdings-sort-key'
const SORT_ORDER_STORAGE_KEY = 'holdings-sort-order'

interface HoldingsListProps {
  holdings: Holding[]
  isLoading: boolean
  error: string | null
  onETFClick?: (code: string) => void
  onHistoryClick?: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  onTradeHistory?: () => void
  onAddTrade?: (code: string, currentPrice?: number) => void
  onAddCashFlow?: () => void
  readOnly?: boolean
  includeSold?: boolean
  onIncludeSoldChange?: (value: boolean) => void
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
  onAddCashFlow,
  readOnly,
  includeSold,
  onIncludeSoldChange,
}: HoldingsListProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'card' || stored === 'table' ? stored : 'table'
  })
  const [pnlMode, setPnlMode] = useState<PnlMode>(() => {
    const stored = localStorage.getItem(PNL_MODE_STORAGE_KEY)
    return stored === 'current' || stored === 'total' ? stored : 'current'
  })
  const [sortKey, setSortKey] = useState<SortKey>(() => {
    const stored = localStorage.getItem(SORT_KEY_STORAGE_KEY)
    return stored && stored in SORT_LABELS
      ? (stored as SortKey)
      : 'current_value'
  })
  const [sortOrder, setSortOrder] = useState<SortOrder>(() => {
    const stored = localStorage.getItem(SORT_ORDER_STORAGE_KEY)
    return stored === 'asc' || stored === 'desc' ? stored : 'desc'
  })

  const cardSortKeys =
    pnlMode === 'current' ? CARD_SORT_KEYS_CURRENT : CARD_SORT_KEYS_TOTAL

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, viewMode)
  }, [viewMode])

  useEffect(() => {
    localStorage.setItem(PNL_MODE_STORAGE_KEY, pnlMode)
  }, [pnlMode])

  useEffect(() => {
    localStorage.setItem(SORT_KEY_STORAGE_KEY, sortKey)
  }, [sortKey])

  useEffect(() => {
    localStorage.setItem(SORT_ORDER_STORAGE_KEY, sortOrder)
  }, [sortOrder])

  const handleViewModeChange = useCallback(
    (mode: ViewMode) => {
      if (mode === 'card' && !cardSortKeys.includes(sortKey)) {
        setSortKey(pnlMode === 'current' ? 'unrealized_pnl' : 'total_pnl')
        setSortOrder('desc')
      }
      setViewMode(mode)
    },
    [sortKey, cardSortKeys, pnlMode]
  )

  const handlePnlModeChange = useCallback(
    (mode: PnlMode) => {
      setPnlMode(mode)
      const newCardSortKeys =
        mode === 'current' ? CARD_SORT_KEYS_CURRENT : CARD_SORT_KEYS_TOTAL
      if (viewMode === 'card' && !newCardSortKeys.includes(sortKey)) {
        setSortKey(mode === 'current' ? 'unrealized_pnl' : 'total_pnl')
        setSortOrder('desc')
      }
    },
    [viewMode, sortKey]
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
        case 'total_pnl':
          aVal = a.total_pnl
          bVal = b.total_pnl
          break
        case 'total_buy_amount':
          aVal = a.total_buy_amount
          bVal = b.total_buy_amount
          break
        case 'total_sell_amount':
          aVal = a.total_sell_amount
          bVal = b.total_sell_amount
          break
        case 'total_pnl_percent':
          aVal = a.total_pnl_percent
          bVal = b.total_pnl_percent
          break
        case 'holding_days':
          aVal = a.holding_days ?? 0
          bVal = b.holding_days ?? 0
          break
        case 'annualized_return': {
          const annKey =
            pnlMode === 'total'
              ? 'annualized_return_total'
              : 'annualized_return'
          aVal = (a[annKey] as number) ?? -Infinity
          bVal = (b[annKey] as number) ?? -Infinity
          break
        }
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
  }, [holdings, sortKey, sortOrder, pnlMode])

  if (isLoading) {
    return <div className={styles.loading}>読み込み中...</div>
  }

  if (error) {
    return <div className={styles.error}>{error}</div>
  }

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        {holdings.length > 0 && (
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
            <div className={styles.pnlModeToggle}>
              <button
                type="button"
                className={`${styles.toggleBtn} ${pnlMode === 'current' ? styles.toggleBtnActive : ''}`}
                onClick={() => handlePnlModeChange('current')}
                aria-label="現在の損益を表示"
                title="現在の損益"
              >
                現在
              </button>
              <button
                type="button"
                className={`${styles.toggleBtn} ${pnlMode === 'total' ? styles.toggleBtnActive : ''}`}
                onClick={() => handlePnlModeChange('total')}
                aria-label="トータルの損益を表示"
                title="トータルの損益"
              >
                トータル
              </button>
            </div>
            {viewMode === 'card' && (
              <select
                className={styles.sortSelect}
                value={`${sortKey}-${sortOrder}`}
                onChange={handleSortSelectChange}
                aria-label="並び替え"
              >
                {cardSortKeys.map((key) => (
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
            {!readOnly && onIncludeSoldChange && (
              <label className={styles.includeSoldLabel}>
                <input
                  type="checkbox"
                  checked={includeSold ?? false}
                  onChange={(e) => onIncludeSoldChange(e.target.checked)}
                  className={styles.includeSoldCheckbox}
                />
                過去保有を含む
              </label>
            )}
          </div>
        )}
        {(readOnly || onTradeHistory || onAddTrade || onAddCashFlow) && (
          <div className={styles.tradeButtons}>
            {(readOnly || onTradeHistory) && (
              <button
                type="button"
                className={styles.tradeHistoryBtn}
                onClick={() => onTradeHistory?.()}
                disabled={readOnly}
              >
                取引履歴
              </button>
            )}
            {(readOnly || onAddTrade) && (
              <button
                type="button"
                className={styles.addTradeBtn}
                onClick={() => onAddTrade?.('')}
                disabled={readOnly}
              >
                取引を追加
              </button>
            )}
            {(readOnly || onAddCashFlow) && (
              <button
                type="button"
                className={styles.addCashFlowBtn}
                onClick={() => onAddCashFlow?.()}
                disabled={readOnly}
              >
                入出金
              </button>
            )}
          </div>
        )}
      </div>

      {holdings.length > 0 ? (
        viewMode === 'table' ? (
          <table className={styles.table}>
            <thead>
              <tr>
                <th
                  onClick={() => handleSortClick('etf_code')}
                  style={{ cursor: 'pointer' }}
                >
                  銘柄{getSortIndicator('etf_code')}
                </th>
                {pnlMode === 'current' && (
                  <th
                    className={styles.right}
                    onClick={() => handleSortClick('quantity')}
                    style={{ cursor: 'pointer' }}
                  >
                    数量{getSortIndicator('quantity')}
                  </th>
                )}
                {pnlMode === 'current' && (
                  <>
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
                  </>
                )}
                {pnlMode === 'current' ? (
                  <>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('current_value')}
                      style={{ cursor: 'pointer' }}
                    >
                      現在評価額{getSortIndicator('current_value')}
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
                  </>
                ) : (
                  <>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('total_buy_amount')}
                      style={{ cursor: 'pointer' }}
                    >
                      累計投資額{getSortIndicator('total_buy_amount')}
                    </th>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('current_value')}
                      style={{ cursor: 'pointer' }}
                    >
                      現在評価額{getSortIndicator('current_value')}
                    </th>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('total_sell_amount')}
                      style={{ cursor: 'pointer' }}
                    >
                      累計売却額{getSortIndicator('total_sell_amount')}
                    </th>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('total_pnl')}
                      style={{ cursor: 'pointer' }}
                    >
                      総利益{getSortIndicator('total_pnl')}
                    </th>
                    <th
                      className={styles.right}
                      onClick={() => handleSortClick('total_pnl_percent')}
                      style={{ cursor: 'pointer' }}
                    >
                      総利益率{getSortIndicator('total_pnl_percent')}
                    </th>
                  </>
                )}
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
                {(readOnly || onHistoryClick || onAddTrade) && (
                  <th className={styles.center}>操作</th>
                )}
                {onCompareToggle && <th className={styles.center}>比較</th>}
              </tr>
            </thead>
            <tbody>
              {sortedHoldings.map((holding) => {
                const pnlClass =
                  holding.unrealized_pnl >= 0
                    ? styles.positive
                    : styles.negative
                const pnlSign = holding.unrealized_pnl >= 0 ? '+' : ''
                const totalPnlClass =
                  holding.total_pnl >= 0 ? styles.positive : styles.negative
                const totalPnlSign = holding.total_pnl >= 0 ? '+' : ''
                const isSold = holding.quantity === 0

                return (
                  <tr
                    key={holding.etf_code}
                    onClick={() => onETFClick?.(holding.etf_code)}
                    className={`${styles.row} ${isSold ? styles.soldRow : ''}`}
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
                          <span className={styles.code}>
                            {holding.etf_code}
                          </span>
                          <MomentumBadge
                            label={holding.etf?.momentum_label}
                            code={holding.etf_code}
                          />
                        </span>
                        <span
                          className={styles.name}
                          title={holding.etf?.name || '-'}
                        >
                          {holding.etf?.name || '-'}
                        </span>
                      </div>
                    </td>
                    {pnlMode === 'current' && (
                      <td className={styles.right}>{holding.quantity}口</td>
                    )}
                    {pnlMode === 'current' && (
                      <>
                        <td className={styles.right}>
                          {formatPrice(holding.average_cost)}
                        </td>
                        <td className={styles.right}>
                          {formatPrice(holding.current_price)}
                        </td>
                      </>
                    )}
                    {pnlMode === 'current' ? (
                      <>
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
                      </>
                    ) : (
                      <>
                        <td className={styles.right}>
                          {formatPrice(holding.total_buy_amount)}
                        </td>
                        <td className={styles.right}>
                          {formatPrice(holding.current_value)}
                        </td>
                        <td className={styles.right}>
                          {formatPrice(holding.total_sell_amount)}
                        </td>
                        <td className={`${styles.right} ${totalPnlClass}`}>
                          {totalPnlSign}
                          {formatPrice(holding.total_pnl)}
                        </td>
                        <td
                          className={`${styles.right} ${
                            holding.total_pnl_percent >= 0
                              ? styles.positive
                              : styles.negative
                          }`}
                        >
                          {holding.total_pnl_percent >= 0 ? '+' : ''}
                          {holding.total_pnl_percent.toFixed(2)}%
                        </td>
                      </>
                    )}
                    <td className={styles.right}>
                      {holding.holding_period || '-'}
                    </td>
                    <td
                      className={`${styles.right} ${(() => {
                        const annVal =
                          pnlMode === 'total'
                            ? holding.annualized_return_total
                            : holding.annualized_return
                        return annVal !== null && annVal !== undefined
                          ? annVal >= 0
                            ? styles.positive
                            : styles.negative
                          : ''
                      })()}`}
                    >
                      {(() => {
                        const annVal =
                          pnlMode === 'total'
                            ? holding.annualized_return_total
                            : holding.annualized_return
                        return annVal !== null && annVal !== undefined
                          ? `${annVal >= 0 ? '+' : ''}${annVal.toFixed(2)}%`
                          : '-'
                      })()}
                    </td>
                    {(readOnly || onHistoryClick || onAddTrade) && (
                      <td
                        className={styles.center}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div
                          style={{
                            display: 'flex',
                            gap: '4px',
                            justifyContent: 'center',
                          }}
                        >
                          {(readOnly || onHistoryClick) && (
                            <button
                              className={styles.historyBtn}
                              onClick={() => onHistoryClick?.(holding.etf_code)}
                              type="button"
                              title="取引履歴"
                              disabled={readOnly}
                            >
                              履歴
                            </button>
                          )}
                          {(readOnly || onAddTrade) && (
                            <button
                              className={styles.tradeBtn}
                              onClick={() =>
                                onAddTrade?.(
                                  holding.etf_code,
                                  holding.current_price
                                )
                              }
                              type="button"
                              title="取引登録"
                              disabled={readOnly}
                            >
                              取引
                            </button>
                          )}
                        </div>
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
                pnlMode={pnlMode}
                onClick={() => onETFClick?.(holding.etf_code)}
                onHistoryClick={
                  onHistoryClick
                    ? () => onHistoryClick(holding.etf_code)
                    : undefined
                }
                onAddTrade={
                  onAddTrade
                    ? () => onAddTrade(holding.etf_code, holding.current_price)
                    : undefined
                }
                isInCompare={isInCompare?.(holding.etf_code)}
                onCompareToggle={
                  onCompareToggle
                    ? () => onCompareToggle(holding.etf_code)
                    : undefined
                }
                readOnly={readOnly}
              />
            ))}
          </div>
        )
      ) : (
        <div className={styles.empty}>
          <p>保有銘柄がありません</p>
          <p className={styles.hint}>取引を登録すると保有銘柄が表示されます</p>
        </div>
      )}
    </div>
  )
}
