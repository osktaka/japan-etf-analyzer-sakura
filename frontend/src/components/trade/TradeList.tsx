/** Trade list component for displaying user's trade history */
import { useState } from 'react'
import { Trade, UpdateTradeRequest } from '../../api/types'
import { formatPrice, formatDate } from '../../utils'
import { TradeForm } from './TradeForm'
import styles from './TradeList.module.css'

interface TradeListProps {
  trades: Trade[]
  isLoading: boolean
  error: string | null
  onUpdate: (id: number, data: UpdateTradeRequest) => Promise<boolean>
  onDelete: (id: number) => Promise<boolean>
  showEtfInfo?: boolean
}

export function TradeList({
  trades,
  isLoading,
  error,
  onUpdate,
  onDelete,
  showEtfInfo = true,
}: TradeListProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleDelete = async (id: number) => {
    if (!confirm('この取引を削除しますか？')) return

    setDeletingId(id)
    await onDelete(id)
    setDeletingId(null)
  }

  const handleUpdate = async (data: UpdateTradeRequest) => {
    if (!editingId) return false
    const success = await onUpdate(editingId, data)
    if (success) {
      setEditingId(null)
    }
    return success
  }

  if (isLoading) {
    return <div className={styles.loading}>読み込み中...</div>
  }

  if (error) {
    return <div className={styles.error}>{error}</div>
  }

  if (trades.length === 0) {
    return <div className={styles.empty}>取引履歴がありません</div>
  }

  return (
    <div className={styles.list}>
      {trades.map((trade) => (
        <div key={trade.id} className={styles.item}>
          {editingId === trade.id ? (
            <TradeForm
              isEdit
              initialData={{
                etf_code: trade.etf_code,
                trade_type: trade.trade_type,
                quantity: trade.quantity,
                price: trade.price,
                trade_date: trade.trade_date,
                memo: trade.memo || undefined,
              }}
              onSubmit={handleUpdate}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <>
              <div className={styles.header}>
                <div className={styles.headerLeft}>
                  <span
                    className={`${styles.type} ${trade.trade_type === 'buy' ? styles.buy : styles.sell}`}
                  >
                    {trade.trade_type === 'buy' ? '買い' : '売り'}
                  </span>
                  {showEtfInfo && trade.etf && (
                    <span className={styles.etfInfo}>
                      <span className={styles.code}>{trade.etf_code}</span>
                      <span className={styles.name}>{trade.etf.name}</span>
                    </span>
                  )}
                  {!showEtfInfo && (
                    <span className={styles.code}>{trade.etf_code}</span>
                  )}
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.editBtn}
                    onClick={() => setEditingId(trade.id)}
                    disabled={deletingId === trade.id}
                  >
                    編集
                  </button>
                  <button
                    className={styles.deleteBtn}
                    onClick={() => handleDelete(trade.id)}
                    disabled={deletingId === trade.id}
                  >
                    {deletingId === trade.id ? '削除中...' : '削除'}
                  </button>
                </div>
              </div>

              <div className={styles.details}>
                <div className={styles.detail}>
                  <span className={styles.label}>数量</span>
                  <span className={styles.value}>{trade.quantity}口</span>
                </div>
                <div className={styles.detail}>
                  <span className={styles.label}>価格</span>
                  <span className={styles.value}>
                    {formatPrice(trade.price)}
                  </span>
                </div>
                <div className={styles.detail}>
                  <span className={styles.label}>合計金額</span>
                  <span className={styles.value}>
                    {formatPrice(trade.total_amount)}
                  </span>
                </div>
                <div className={styles.detail}>
                  <span className={styles.label}>取引日</span>
                  <span className={styles.value}>
                    {formatDate(trade.trade_date)}
                  </span>
                </div>
              </div>

              {trade.memo && (
                <div className={styles.memo}>
                  <span className={styles.label}>メモ</span>
                  <p>{trade.memo}</p>
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  )
}
