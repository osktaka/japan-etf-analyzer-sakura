/** Trade history modal component for viewing and filtering trade history */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks'
import { tradesApi } from '../../api/trades'
import { cashFlowsApi } from '../../api/cashFlows'
import { Trade, CashFlow, TradeFilterOptions } from '../../api/types'
import { ROUTES, formatPrice } from '../../utils'
import { TradeFormModal } from './TradeFormModal'
import { CashFlowFormModal } from './CashFlowFormModal'
import styles from './TradeHistoryModal.module.css'

type TimelineEntry =
  | { type: 'trade'; data: Trade; date: string }
  | { type: 'cash_flow'; data: CashFlow; date: string }

interface TradeHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  initialSearch?: string
  onSuccess?: () => void
}

export function TradeHistoryModal({
  isOpen,
  onClose,
  initialSearch = '',
  onSuccess,
}: TradeHistoryModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [trades, setTrades] = useState<Trade[]>([])
  const [cashFlows, setCashFlows] = useState<CashFlow[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingTrade, setEditingTrade] = useState<Trade | null>(null)
  const [editingCashFlow, setEditingCashFlow] = useState<CashFlow | null>(null)
  const [isAddFormOpen, setIsAddFormOpen] = useState(false)
  const [isCashFlowFormOpen, setIsCashFlowFormOpen] = useState(false)
  const [deletingTradeId, setDeletingTradeId] = useState<number | null>(null)
  const [deletingCashFlowId, setDeletingCashFlowId] = useState<number | null>(
    null
  )

  // Filter states
  const [search, setSearch] = useState(initialSearch)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchData = useCallback(
    async (searchOverride?: string) => {
      setIsLoading(true)
      setError(null)
      try {
        const tradeOptions: TradeFilterOptions = {}
        const currentSearch =
          searchOverride !== undefined ? searchOverride : search
        if (currentSearch.trim()) {
          tradeOptions.search = currentSearch.trim()
        }
        if (startDate) {
          tradeOptions.startDate = startDate
        }
        if (endDate) {
          tradeOptions.endDate = endDate
        }

        const cashFlowOptions: { startDate?: string; endDate?: string } = {}
        if (startDate) {
          cashFlowOptions.startDate = startDate
        }
        if (endDate) {
          cashFlowOptions.endDate = endDate
        }

        // 銘柄検索時は入出金を含めない（入出金は銘柄に紐付かないため）
        const shouldFetchCashFlows = !currentSearch.trim()
        const [tradesData, cashFlowsData] = await Promise.all([
          tradesApi.getAll(undefined, tradeOptions),
          shouldFetchCashFlows
            ? cashFlowsApi.getAll(
                Object.keys(cashFlowOptions).length > 0
                  ? cashFlowOptions
                  : undefined
              )
            : Promise.resolve([]),
        ])
        setTrades(tradesData)
        setCashFlows(cashFlowsData)
      } catch {
        setError('取引履歴の取得に失敗しました')
      } finally {
        setIsLoading(false)
      }
    },
    [search, startDate, endDate]
  )

  // Build unified timeline
  const timeline = useMemo(() => {
    const entries: TimelineEntry[] = [
      ...trades.map((t) => ({
        type: 'trade' as const,
        data: t,
        date: t.trade_date,
      })),
      ...cashFlows.map((cf) => ({
        type: 'cash_flow' as const,
        data: cf,
        date: cf.flow_date,
      })),
    ]
    return entries.sort((a, b) => b.date.localeCompare(a.date))
  }, [trades, cashFlows])

  // Fetch data when modal opens
  useEffect(() => {
    if (isOpen && isAuthenticated) {
      fetchData(initialSearch)
    }
  }, [isOpen, isAuthenticated, initialSearch, startDate, endDate, fetchData])

  // Initialize search when modal opens
  useEffect(() => {
    if (isOpen) {
      setSearch(initialSearch)
    }
  }, [isOpen, initialSearch])

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setStartDate('')
      setEndDate('')
      setTrades([])
      setCashFlows([])
      setError(null)
      setEditingTrade(null)
      setEditingCashFlow(null)
      setIsAddFormOpen(false)
      setIsCashFlowFormOpen(false)
    }
  }, [isOpen])

  const handleEdit = (trade: Trade) => {
    setEditingTrade(trade)
  }

  const handleCashFlowEdit = (cashFlow: CashFlow) => {
    setEditingCashFlow(cashFlow)
  }

  const handleFormSuccess = () => {
    fetchData()
    setEditingTrade(null)
    setEditingCashFlow(null)
    setIsAddFormOpen(false)
    setIsCashFlowFormOpen(false)
    onSuccess?.()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('この取引を削除しますか？')) return

    setDeletingTradeId(id)
    try {
      await tradesApi.delete(id)
      await fetchData()
      onSuccess?.()
    } catch {
      setError('削除に失敗しました')
    } finally {
      setDeletingTradeId(null)
    }
  }

  const handleCashFlowDelete = async (id: number) => {
    if (!confirm('この入出金を削除しますか？')) return

    setDeletingCashFlowId(id)
    try {
      await cashFlowsApi.delete(id)
      await fetchData()
      onSuccess?.()
    } catch {
      setError('削除に失敗しました')
    } finally {
      setDeletingCashFlowId(null)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}/${month}/${day}`
  }

  if (!isOpen) return null

  const handleLogin = () => {
    onClose()
    navigate(ROUTES.LOGIN)
  }

  const handleRegister = () => {
    onClose()
    navigate(ROUTES.REGISTER)
  }

  // 未ログイン時はログイン促進表示
  if (!isAuthenticated) {
    return (
      <div className={styles.overlay} onClick={onClose}>
        <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
          <div className={styles.content}>
            <div className={styles.icon}>&#x1f4cb;</div>
            <h2 className={styles.title}>取引履歴</h2>
            <p className={styles.description}>
              取引履歴機能はログイン後にご利用いただけます。
            </p>
            <div className={styles.buttons}>
              <button className="btn btn-primary" onClick={handleLogin}>
                ログイン
              </button>
              <button className="btn btn-secondary" onClick={handleRegister}>
                新規登録
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const renderTimelineContent = () => {
    if (isLoading) {
      return <div className={styles.statusMessage}>読み込み中...</div>
    }

    if (error) {
      return <div className={styles.errorMessage}>{error}</div>
    }

    if (timeline.length === 0) {
      return <div className={styles.statusMessage}>取引履歴がありません</div>
    }

    return (
      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>日付</th>
              <th>銘柄</th>
              <th className={styles.numericHeader}>数量</th>
              <th className={styles.numericHeader}>価格</th>
              <th className={styles.numericHeader}>合計</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {timeline.map((entry) => {
              if (entry.type === 'trade') {
                const trade = entry.data
                return (
                  <tr key={`trade-${trade.id}`}>
                    <td className={styles.dateCell} data-label="">
                      <div className={styles.dateContent}>
                        <span className={styles.date}>
                          {formatDate(trade.trade_date)}
                        </span>
                        <span
                          className={`${styles.typeBadge} ${trade.trade_type === 'buy' ? styles.buy : styles.sell}`}
                        >
                          {trade.trade_type === 'buy' ? '買い' : '売り'}
                        </span>
                      </div>
                    </td>
                    <td className={styles.etfCell} data-label="">
                      <div className={styles.etfInfo}>
                        <span className={styles.code}>{trade.etf_code}</span>
                        {trade.etf && (
                          <span className={styles.etfName}>
                            {trade.etf.name}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className={styles.numericCell} data-label="数量">
                      {trade.quantity}口
                    </td>
                    <td className={styles.numericCell} data-label="価格">
                      {formatPrice(trade.price)}
                    </td>
                    <td className={styles.numericCell} data-label="合計">
                      {formatPrice(trade.total_amount)}
                    </td>
                    <td className={styles.actionsCell}>
                      <div className={styles.actions}>
                        <button
                          className={styles.editBtn}
                          onClick={() => handleEdit(trade)}
                          disabled={deletingTradeId === trade.id}
                        >
                          編集
                        </button>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleDelete(trade.id)}
                          disabled={deletingTradeId === trade.id}
                        >
                          {deletingTradeId === trade.id ? '削除中...' : '削除'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              } else {
                const cashFlow = entry.data
                return (
                  <tr key={`cf-${cashFlow.id}`}>
                    <td className={styles.dateCell} data-label="">
                      <div className={styles.dateContent}>
                        <span className={styles.date}>
                          {formatDate(cashFlow.flow_date)}
                        </span>
                        <span
                          className={`${styles.cashFlowType} ${cashFlow.flow_type === 'deposit' ? styles.deposit : styles.withdrawal}`}
                        >
                          {cashFlow.flow_type === 'deposit' ? '入金' : '出金'}
                        </span>
                      </div>
                    </td>
                    <td className={styles.dashCell} data-label="">
                      --
                    </td>
                    <td className={styles.dashCell} data-label="数量">
                      --
                    </td>
                    <td className={styles.dashCell} data-label="価格">
                      --
                    </td>
                    <td className={styles.numericCell} data-label="合計">
                      {formatPrice(cashFlow.amount)}
                    </td>
                    <td className={styles.actionsCell}>
                      <div className={styles.actions}>
                        <button
                          className={styles.editBtn}
                          onClick={() => handleCashFlowEdit(cashFlow)}
                          disabled={deletingCashFlowId === cashFlow.id}
                        >
                          編集
                        </button>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleCashFlowDelete(cashFlow.id)}
                          disabled={deletingCashFlowId === cashFlow.id}
                        >
                          {deletingCashFlowId === cashFlow.id
                            ? '削除中...'
                            : '削除'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              }
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <>
      <div className={styles.overlay} onClick={onClose}>
        <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
          <div className={styles.content}>
            <h2 className={styles.title}>取引履歴</h2>

            <div className={styles.filters}>
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>銘柄検索</label>
                <input
                  type="text"
                  className={styles.filterInput}
                  placeholder="銘柄コード・名前で検索"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>開始日</label>
                <input
                  type="date"
                  className={styles.filterInput}
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>終了日</label>
                <input
                  type="date"
                  className={styles.filterInput}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            <div className={styles.actionBar}>
              <button
                className="btn btn-primary"
                onClick={() => setIsAddFormOpen(true)}
              >
                取引を追加
              </button>
              <button
                className={styles.addCashFlowButton}
                onClick={() => setIsCashFlowFormOpen(true)}
              >
                入出金
              </button>
            </div>

            <div className={styles.listContainer}>
              {renderTimelineContent()}
            </div>
          </div>
        </div>
      </div>

      <TradeFormModal
        isOpen={isAddFormOpen || editingTrade !== null}
        onClose={() => {
          setIsAddFormOpen(false)
          setEditingTrade(null)
        }}
        onSuccess={handleFormSuccess}
        trade={editingTrade ?? undefined}
        isEdit={editingTrade !== null}
        defaultEtfCode={search}
      />

      <CashFlowFormModal
        isOpen={isCashFlowFormOpen || editingCashFlow !== null}
        onClose={() => {
          setIsCashFlowFormOpen(false)
          setEditingCashFlow(null)
        }}
        onSuccess={handleFormSuccess}
        cashFlow={editingCashFlow ?? undefined}
        isEdit={editingCashFlow !== null}
      />
    </>
  )
}
