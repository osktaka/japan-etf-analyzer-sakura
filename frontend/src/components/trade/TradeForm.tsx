/** Trade form component for creating/editing trades */
import { useState, FormEvent } from 'react'
import { CreateTradeRequest } from '../../api/types'
import { ETFCodeAutocomplete } from '../common'
import styles from './TradeForm.module.css'

interface TradeFormProps {
  etfCode?: string
  initialData?: Partial<CreateTradeRequest>
  defaultPrice?: number
  onSubmit: (data: CreateTradeRequest) => Promise<boolean>
  onCancel: () => void
  isEdit?: boolean
}

export function TradeForm({
  etfCode: defaultEtfCode,
  initialData,
  defaultPrice,
  onSubmit,
  onCancel,
  isEdit = false,
}: TradeFormProps) {
  const [etfCode, setEtfCode] = useState(
    initialData?.etf_code || defaultEtfCode || ''
  )
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>(
    initialData?.trade_type || 'buy'
  )
  const [quantity, setQuantity] = useState(
    initialData?.quantity?.toString() || ''
  )
  const [price, setPrice] = useState(
    initialData?.price?.toString() ||
      (defaultPrice != null ? defaultPrice.toString() : '')
  )
  const [tradeDate, setTradeDate] = useState(
    initialData?.trade_date || new Date().toISOString().split('T')[0]
  )
  const [memo, setMemo] = useState(initialData?.memo || '')
  const [selectedEtfName, setSelectedEtfName] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!etfCode.trim()) {
      setError('ETFコードを入力してください')
      return
    }
    if (!quantity || parseInt(quantity) <= 0) {
      setError('数量は1以上を入力してください')
      return
    }
    if (!price || parseFloat(price) <= 0) {
      setError('価格は0より大きい値を入力してください')
      return
    }

    setIsSubmitting(true)

    const data: CreateTradeRequest = {
      etf_code: etfCode.trim(),
      trade_type: tradeType,
      quantity: parseInt(quantity),
      price: parseFloat(price),
      trade_date: tradeDate,
      memo: memo.trim() || undefined,
    }

    const success = await onSubmit(data)

    if (success) {
      if (!isEdit) {
        setQuantity('')
        setPrice('')
        setMemo('')
      }
    } else {
      setError('登録に失敗しました')
    }

    setIsSubmitting(false)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <h3 className={styles.title}>{isEdit ? '取引を編集' : '取引を登録'}</h3>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.field}>
        <label htmlFor="etfCode">ETFコード</label>
        <ETFCodeAutocomplete
          id="etfCode"
          value={etfCode}
          onChange={setEtfCode}
          onSelect={(_code, name, marketPrice) => {
            setSelectedEtfName(name)
            if (marketPrice != null) {
              setPrice(marketPrice.toString())
            }
          }}
          onFocus={(e) => e.target.select()}
          placeholder="例: 1306"
          disabled={isEdit}
          required
        />
        {selectedEtfName && (
          <span className={styles.etfName}>{selectedEtfName}</span>
        )}
      </div>

      <div className={styles.field}>
        <label>取引種別</label>
        <div className={styles.radioGroup}>
          <label className={styles.radio}>
            <input
              type="radio"
              name="tradeType"
              value="buy"
              checked={tradeType === 'buy'}
              onChange={() => setTradeType('buy')}
            />
            <span className={styles.radioLabel}>買い</span>
          </label>
          <label className={styles.radio}>
            <input
              type="radio"
              name="tradeType"
              value="sell"
              checked={tradeType === 'sell'}
              onChange={() => setTradeType('sell')}
            />
            <span className={styles.radioLabel}>売り</span>
          </label>
        </div>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label htmlFor="quantity">数量</label>
          <input
            id="quantity"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="例: 10"
            min="1"
            required
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="price">価格（円）</label>
          <input
            id="price"
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="例: 2345"
            min="0.01"
            step="0.01"
            required
          />
        </div>
      </div>

      <div className={styles.field}>
        <label htmlFor="tradeDate">取引日</label>
        <input
          id="tradeDate"
          type="date"
          value={tradeDate}
          onChange={(e) => setTradeDate(e.target.value)}
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
