/** Cash flow form modal component for adding/editing deposits and withdrawals */
import { cashFlowsApi } from '../../api/cashFlows'
import { CreateCashFlowRequest, CashFlow } from '../../api/types'
import { CashFlowForm } from '../cashflow/CashFlowForm'
import styles from './TradeFormModal.module.css'

interface CashFlowFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  cashFlow?: CashFlow
  isEdit?: boolean
  defaultFlowType?: 'deposit' | 'withdrawal'
}

export function CashFlowFormModal({
  isOpen,
  onClose,
  onSuccess,
  cashFlow,
  isEdit = false,
  defaultFlowType,
}: CashFlowFormModalProps) {
  if (!isOpen) return null

  const handleSubmit = async (
    data: CreateCashFlowRequest
  ): Promise<boolean> => {
    try {
      if (isEdit && cashFlow) {
        await cashFlowsApi.update(cashFlow.id, data)
      } else {
        await cashFlowsApi.create(data)
      }
      onSuccess?.()
      onClose()
      return true
    } catch {
      return false
    }
  }

  const initialData = cashFlow
    ? {
        flow_type: cashFlow.flow_type,
        amount: cashFlow.amount,
        flow_date: cashFlow.flow_date,
        memo: cashFlow.memo || undefined,
      }
    : defaultFlowType
      ? { flow_type: defaultFlowType }
      : { flow_type: 'deposit' as const }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>
            {isEdit ? '入出金編集' : '入出金登録'}
          </h2>
          <CashFlowForm
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
