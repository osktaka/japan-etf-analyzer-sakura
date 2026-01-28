/** Trade history modal component for viewing and filtering trade history */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks'
import { tradesApi } from '../../api/trades'
import { Trade, UpdateTradeRequest, TradeFilterOptions } from '../../api/types'
import { ROUTES } from '../../utils'
import { TradeList } from '../trade/TradeList'
import styles from './TradeHistoryModal.module.css'

interface TradeHistoryModalProps {
  isOpen: boolean
  onClose: () => void
}

export function TradeHistoryModal({ isOpen, onClose }: TradeHistoryModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [trades, setTrades] = useState<Trade[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter states
  const [search, setSearch] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchTrades = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const options: TradeFilterOptions = {}
      if (search.trim()) {
        options.search = search.trim()
      }
      if (startDate) {
        options.startDate = startDate
      }
      if (endDate) {
        options.endDate = endDate
      }
      const data = await tradesApi.getAll(undefined, options)
      setTrades(data)
    } catch {
      setError('取引履歴の取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }, [search, startDate, endDate])

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      fetchTrades()
    }
  }, [isOpen, isAuthenticated, fetchTrades])

  // Reset filters when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSearch('')
      setStartDate('')
      setEndDate('')
      setTrades([])
      setError(null)
    }
  }, [isOpen])

  const handleUpdate = async (
    id: number,
    data: UpdateTradeRequest
  ): Promise<boolean> => {
    try {
      await tradesApi.update(id, data)
      await fetchTrades()
      return true
    } catch {
      return false
    }
  }

  const handleDelete = async (id: number): Promise<boolean> => {
    try {
      await tradesApi.delete(id)
      await fetchTrades()
      return true
    } catch {
      return false
    }
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
            <div className={styles.icon}>📋</div>
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
            <button className={styles.closeLink} onClick={onClose}>
              閉じる
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
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
            <div className={styles.filterRow}>
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
          </div>

          <div className={styles.listContainer}>
            <TradeList
              trades={trades}
              isLoading={isLoading}
              error={error}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              showEtfInfo={true}
            />
          </div>

          <button className={styles.closeLink} onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  )
}
