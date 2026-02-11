/** Cash flow form component for creating/editing deposits and withdrawals */
import { useState, FormEvent } from 'react'
import { CreateCashFlowRequest } from '../../api/types'
import styles from './CashFlowForm.module.css'

interface CashFlowFormProps {
  initialData?: Partial<CreateCashFlowRequest>
  onSubmit: (data: CreateCashFlowRequest) => Promise<boolean>
  onCancel: () => void
  isEdit?: boolean
}

export function CashFlowForm({
  initialData,
  onSubmit,
  onCancel,
  isEdit = false,
}: CashFlowFormProps) {
  const [flowType, setFlowType] = useState<'deposit' | 'withdrawal'>(
    initialData?.flow_type || 'deposit'
  )
  const [amount, setAmount] = useState(
    initialData?.amount?.toString() || ''
  )
  const [flowDate, setFlowDate] = useState(
    initialData?.flow_date || new Date().toISOString().split('T')[0]
  )
  const [memo, setMemo] = useState(initialData?.memo || '')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    const parsedAmount = parseInt(amount, 10)
    if (!amount || isNaN(parsedAmount) || parsedAmount <= 0) {
      setError('金額は1以上の数値を入力してください')
      return
    }

    const today = new Date().toISOString().split('T')[0]
    if (flowDate > today) {
      setError('未来の日付は指定できません')
      return
    }

    setIsSubmitting(true)

    const data: CreateCashFlowRequest = {
      flow_type: flowType,
      amount: parseInt(amount),
      flow_date: flowDate,
      memo: memo.trim() || undefined,
    }

    const success = await onSubmit(data)

    if (success) {
      if (!isEdit) {
        setAmount('')
        setMemo('')
      }
    } else {
      setError('登録に失敗しました')
    }

    setIsSubmitting(false)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <h3 className={styles.title}>
        {isEdit ? '入出金を編集' : '入出金を登録'}
      </h3>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.field}>
        <label>種別</label>
        <div className={styles.radioGroup}>
          <label className={styles.radio}>
            <input
              type="radio"
              name="flowType"
              value="deposit"
              checked={flowType === 'deposit'}
              onChange={() => setFlowType('deposit')}
            />
            <span className={styles.radioLabel}>入金</span>
          </label>
          <label className={styles.radio}>
            <input
              type="radio"
              name="flowType"
              value="withdrawal"
              checked={flowType === 'withdrawal'}
              onChange={() => setFlowType('withdrawal')}
            />
            <span className={styles.radioLabel}>出金</span>
          </label>
        </div>
      </div>

      <div className={styles.field}>
        <label htmlFor="amount">金額（円）</label>
        <input
          id="amount"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="例: 100000"
          min="1"
          step="1"
          required
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="flowDate">日付</label>
        <input
          id="flowDate"
          type="date"
          value={flowDate}
          onChange={(e) => setFlowDate(e.target.value)}
          max={new Date().toISOString().split('T')[0]}
          required
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="memo">メモ（任意）</label>
        <textarea
          id="memo"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="メモを入力..."
          rows={3}
        />
      </div>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.cancelBtn}
          onClick={onCancel}
          disabled={isSubmitting}
        >
          キャンセル
        </button>
        <button
          type="submit"
          className={styles.submitBtn}
          disabled={isSubmitting}
        >
          {isSubmitting ? '処理中...' : isEdit ? '更新' : '登録'}
        </button>
      </div>
    </form>
  )
}
