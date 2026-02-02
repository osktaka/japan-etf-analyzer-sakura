/** Custom weights modal component */
import { useState, useEffect, useRef } from 'react'
import { CustomWeights } from '../../api/types'
import styles from './CustomWeightsModal.module.css'

interface CustomWeightsModalProps {
  isOpen: boolean
  onClose: () => void
  currentWeights: CustomWeights | null
  onSave: (weights: CustomWeights) => Promise<void>
}

const AXIS_LABELS = {
  dividend_power: '配当力',
  cost_efficiency: 'コスト効率',
  scale_reliability: '安定性',
  trading_quality: '取引規模',
  return_performance: 'リターン実績',
} as const

const AXIS_DESCRIPTIONS = {
  dividend_power: '配当利回りの高さ',
  cost_efficiency: '信託報酬の低さ',
  scale_reliability: '純資産総額の大きさ',
  trading_quality: '売買代金・出来高の多さ',
  return_performance: '1年・3年リターンの高さ',
} as const

const DEFAULT_WEIGHTS: CustomWeights = {
  dividend_power: 20,
  cost_efficiency: 20,
  scale_reliability: 20,
  trading_quality: 20,
  return_performance: 20,
}

export function CustomWeightsModal({
  isOpen,
  onClose,
  currentWeights,
  onSave,
}: CustomWeightsModalProps) {
  const [weights, setWeights] = useState<CustomWeights>(
    currentWeights || DEFAULT_WEIGHTS
  )
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTooltip, setActiveTooltip] = useState<keyof CustomWeights | null>(null)
  const tooltipRefs = useRef<{ [key in keyof CustomWeights]?: HTMLDivElement | null }>({})

  // currentWeightsが変更されたら内部状態を更新
  useEffect(() => {
    if (isOpen) {
      if (currentWeights) {
        // バックエンドから受け取った0-1形式を0-100形式に変換
        setWeights({
          dividend_power: Math.round(currentWeights.dividend_power * 100),
          cost_efficiency: Math.round(currentWeights.cost_efficiency * 100),
          scale_reliability: Math.round(currentWeights.scale_reliability * 100),
          trading_quality: Math.round(currentWeights.trading_quality * 100),
          return_performance: Math.round(currentWeights.return_performance * 100),
        })
      } else {
        setWeights(DEFAULT_WEIGHTS)
      }
      setError(null)
    }
  }, [isOpen, currentWeights])

  // 枠外クリックでツールチップを閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (activeTooltip) {
        const tooltipElement = tooltipRefs.current[activeTooltip]
        if (tooltipElement && !tooltipElement.contains(event.target as Node)) {
          setActiveTooltip(null)
        }
      }
    }

    if (activeTooltip) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [activeTooltip])

  if (!isOpen) return null

  const total = Object.values(weights).reduce((sum, val) => sum + val, 0)
  const isValid = total === 100

  const handleChange = (key: keyof CustomWeights, value: string) => {
    const numValue = parseInt(value, 10)
    if (isNaN(numValue) || numValue < 0 || numValue > 100) return
    setWeights((prev) => ({ ...prev, [key]: numValue }))
  }

  const handleLabelClick = (key: keyof CustomWeights) => {
    setActiveTooltip((prev) => (prev === key ? null : key))
  }

  const handleSave = async () => {
    if (!isValid) {
      setError('合計が100%になるように調整してください')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      // バックエンドAPIは0-100形式を期待しているのでそのまま送信
      await onSave(weights)
      onClose()
    } catch (err) {
      setError('保存に失敗しました')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>カスタム重みづけ設定</h2>
          <p className={styles.description}>
            各評価軸の重みを0〜100の範囲で設定してください。合計は100%にする必要があります。
          </p>

          <div className={styles.form}>
            {(Object.keys(AXIS_LABELS) as Array<keyof CustomWeights>).map(
              (key) => (
                <div key={key} className={styles.field}>
                  <div className={styles.labelWrapper}>
                    <span
                      className={styles.labelClickable}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleLabelClick(key)
                      }}
                      aria-label={`${AXIS_LABELS[key]}の詳細を表示`}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          e.stopPropagation()
                          handleLabelClick(key)
                        }
                      }}
                    >
                      {AXIS_LABELS[key]}
                    </span>
                    {activeTooltip === key && (
                      <div
                        ref={(el) => {
                          tooltipRefs.current[key] = el
                        }}
                        className={styles.tooltip}
                      >
                        {AXIS_DESCRIPTIONS[key]}
                      </div>
                    )}
                  </div>
                  <div className={styles.sliderGroup}>
                    <input
                      type="range"
                      id={key}
                      min="0"
                      max="100"
                      step="5"
                      value={weights[key]}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className={styles.slider}
                    />
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={weights[key]}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className={styles.valueInput}
                    />
                    <span className={styles.unit}>%</span>
                  </div>
                  <label htmlFor={key} className={styles.srOnly}>
                    {AXIS_LABELS[key]}
                  </label>
                </div>
              )
            )}
          </div>

          <div className={styles.total}>
            <span className={styles.totalLabel}>合計:</span>
            <span
              className={`${styles.totalValue} ${isValid ? styles.valid : styles.invalid}`}
            >
              {total}%
            </span>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.buttons}>
            <button
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              キャンセル
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={!isValid || isSaving}
            >
              {isSaving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
