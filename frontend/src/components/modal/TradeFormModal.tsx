/** Trade form modal component for adding trades */
import { tradesApi } from '../../api/trades'
import { CreateTradeRequest } from '../../api/types'
import { TradeForm } from '../trade/TradeForm'
import styles from './TradeFormModal.module.css'

interface TradeFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function TradeFormModal({
  isOpen,
  onClose,
  onSuccess,
}: TradeFormModalProps) {
  if (!isOpen) return null

  const handleSubmit = async (data: CreateTradeRequest): Promise<boolean> => {
    try {
      await tradesApi.create(data)
      onSuccess?.()
      onClose()
      return true
    } catch {
      return false
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <TradeForm onSubmit={handleSubmit} onCancel={onClose} />
        </div>
      </div>
    </div>
  )
}
