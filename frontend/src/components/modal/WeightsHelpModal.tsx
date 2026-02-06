/** Weights help modal component */
import { useState, useEffect, useRef } from 'react'
import { CustomWeights } from '../../api'
import styles from './WeightsHelpModal.module.css'

type AxisKey = 'dividend' | 'cost' | 'stability' | 'scale' | 'return'

const HEADER_LABELS: Record<AxisKey, string> = {
  dividend: '配当',
  cost: 'コスト',
  stability: '安定',
  scale: '規模',
  return: 'リターン',
}

const AXIS_DESCRIPTIONS: Record<AxisKey, string> = {
  dividend: '配当利回りの高さ',
  cost: '信託報酬の低さ',
  stability: '純資産総額の大きさ',
  scale: '売買代金・出来高の多さ',
  return: '1年・3年リターンの高さ',
}

interface WeightsHelpModalProps {
  isOpen: boolean
  onClose: () => void
  isAuthenticated?: boolean
  customWeights?: CustomWeights | null
  onEditCustom?: () => void
}

export function WeightsHelpModal({
  isOpen,
  onClose,
  isAuthenticated = false,
  customWeights = null,
  onEditCustom,
}: WeightsHelpModalProps) {
  const [activeTooltip, setActiveTooltip] = useState<AxisKey | null>(null)
  const tooltipRefs = useRef<{ [key in AxisKey]?: HTMLDivElement | null }>({})

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

  const handleHeaderClick = (key: AxisKey) => {
    setActiveTooltip((prev) => (prev === key ? null : key))
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>評価スコアの重みづけ</h2>
          <p className={styles.description}>
            切り口ごとに評価の重みづけが異なります。
          </p>
          <table className={styles.helpTable}>
            <thead>
              <tr>
                <th>切り口</th>
                {(Object.keys(HEADER_LABELS) as AxisKey[]).map((key) => (
                  <th key={key} className={styles.headerWrapper}>
                    <span
                      className={styles.headerClickable}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleHeaderClick(key)
                      }}
                      aria-label={`${HEADER_LABELS[key]}の詳細を表示`}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          e.stopPropagation()
                          handleHeaderClick(key)
                        }
                      }}
                    >
                      {HEADER_LABELS[key]}
                    </span>
                    {activeTooltip === key && (
                      <div
                        ref={(el) => {
                          tooltipRefs.current[key] = el
                        }}
                        className={styles.headerTooltip}
                      >
                        {AXIS_DESCRIPTIONS[key]}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>バランス</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
              </tr>
              <tr>
                <td>配当収入</td>
                <td className={styles.highlight}>50</td>
                <td>10</td>
                <td>20</td>
                <td>10</td>
                <td>10</td>
              </tr>
              <tr>
                <td>低コスト</td>
                <td>10</td>
                <td className={styles.highlight}>50</td>
                <td>20</td>
                <td>10</td>
                <td>10</td>
              </tr>
              <tr>
                <td>安定性</td>
                <td>10</td>
                <td>20</td>
                <td className={styles.highlight}>40</td>
                <td>20</td>
                <td>10</td>
              </tr>
              <tr>
                <td>取引規模</td>
                <td>10</td>
                <td>10</td>
                <td>20</td>
                <td className={styles.highlight}>50</td>
                <td>10</td>
              </tr>
              <tr>
                <td>成長性</td>
                <td>10</td>
                <td>10</td>
                <td>20</td>
                <td>10</td>
                <td className={styles.highlight}>50</td>
              </tr>
              <tr>
                <td className={styles.customLabel}>カスタム</td>
                <td>
                  {isAuthenticated
                    ? (customWeights?.dividend_power != null
                        ? Math.round(customWeights.dividend_power * 100)
                        : '-')
                    : '-'}
                </td>
                <td>
                  {isAuthenticated
                    ? (customWeights?.cost_efficiency != null
                        ? Math.round(customWeights.cost_efficiency * 100)
                        : '-')
                    : '-'}
                </td>
                <td>
                  {isAuthenticated
                    ? (customWeights?.scale_reliability != null
                        ? Math.round(customWeights.scale_reliability * 100)
                        : '-')
                    : '-'}
                </td>
                <td>
                  {isAuthenticated
                    ? (customWeights?.trading_quality != null
                        ? Math.round(customWeights.trading_quality * 100)
                        : '-')
                    : '-'}
                </td>
                <td>
                  {isAuthenticated
                    ? (customWeights?.return_performance != null
                        ? Math.round(customWeights.return_performance * 100)
                        : '-')
                    : '-'}
                </td>
              </tr>
            </tbody>
          </table>
          {isAuthenticated && onEditCustom && (
            <div className={styles.editLinkWrapper}>
              <button
                className={styles.editLink}
                onClick={(e) => {
                  e.stopPropagation()
                  onEditCustom()
                }}
              >
                カスタムを編集
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
