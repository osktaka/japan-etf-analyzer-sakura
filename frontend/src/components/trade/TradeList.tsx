/** Trade list component for displaying user's trade history in table format */
import { useState } from 'react'
import { Trade } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './TradeList.module.css'

interface TradeListProps {
  trades: Trade[]
  isLoading: boolean
  error: string | null
  onEdit?: (trade: Trade) => void
  onDelete: (id: number) => Promise<boolean>
  showEtfInfo?: boolean
}

export function TradeList({
  trades,
  isLoading,
  error,
  onEdit,
  onDelete,
  showEtfInfo = true,
}: TradeListProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleDelete = async (id: number) => {
    if (!confirm('この取引を削除しますか？')) return

    setDeletingId(id)
    await onDelete(id)
    setDeletingId(null)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}/${month}/${day}`
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
    <div className={styles.tableContainer}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>日付</th>
            {showEtfInfo && <th>銘柄</th>}
            <th className={styles.numericHeader}>数量</th>
            <th className={styles.numericHeader}>価格</th>
            <th className={styles.numericHeader}>合計</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <tr key={trade.id}>
              <td className={styles.dateCell} data-label="日付">
                <div className={styles.dateContent}>
                  <span className={styles.date}>{formatDate(trade.trade_date)}</span>
                  <span
                    className={`${styles.type} ${trade.trade_type === 'buy' ? styles.buy : styles.sell}`}
                  >
                    {trade.trade_type === 'buy' ? '買い' : '売り'}
                  </span>
                </div>
              </td>
              {showEtfInfo && (
                <td className={styles.etfCell} data-label="銘柄">
                  <span className={styles.code}>{trade.etf_code}</span>
                  {trade.etf && (
                    <span className={styles.name}>{trade.etf.name}</span>
                  )}
                </td>
              )}
              <td className={styles.numericCell} data-label="数量">{trade.quantity}口</td>
              <td className={styles.numericCell} data-label="価格">{formatPrice(trade.price)}</td>
              <td className={styles.numericCell} data-label="合計">{formatPrice(trade.total_amount)}</td>
              <td className={styles.actionsCell}>
                <div className={styles.actions}>
                  {onEdit && (
                    <button
                      className={styles.editBtn}
                      onClick={() => onEdit(trade)}
                      disabled={deletingId === trade.id}
                    >
                      編集
                    </button>
                  )}
                  <button
                    className={styles.deleteBtn}
                    onClick={() => handleDelete(trade.id)}
                    disabled={deletingId === trade.id}
                  >
                    {deletingId === trade.id ? '削除中...' : '削除'}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
