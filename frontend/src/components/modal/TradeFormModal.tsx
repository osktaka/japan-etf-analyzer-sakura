/** Trade form modal component for adding/editing trades */
import { tradesApi } from '../../api/trades'
import { CreateTradeRequest, Trade } from '../../api/types'
import { TradeForm } from '../trade/TradeForm'
import styles from './TradeFormModal.module.css'

interface TradeFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  trade?: Trade
  isEdit?: boolean
  defaultEtfCode?: string
}

export function TradeFormModal({
  isOpen,
  onClose,
  onSuccess,
  trade,
  isEdit = false,
  defaultEtfCode,
}: TradeFormModalProps) {
  if (!isOpen) return null

  const handleSubmit = async (data: CreateTradeRequest): Promise<boolean> => {
    try {
      if (isEdit && trade) {
        await tradesApi.update(trade.id, data)
      } else {
        await tradesApi.create(data)
      }
      onSuccess?.()
      onClose()
      return true
    } catch {
      return false
    }
  }

  const initialData = trade
    ? {
        etf_code: trade.etf_code,
        trade_type: trade.trade_type,
        quantity: trade.quantity,
        price: trade.price,
        trade_date: trade.trade_date,
        memo: trade.memo || undefined,
      }
    : undefined

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>{isEdit ? '取引編集' : '取引登録'}</h2>
          <TradeForm
            etfCode={defaultEtfCode}
            initialData={initialData}
            isEdit={isEdit}
            onSubmit={handleSubmit}
            onCancel={onClose}
          />
        </div>
      </div>
    </div>
  )
}
