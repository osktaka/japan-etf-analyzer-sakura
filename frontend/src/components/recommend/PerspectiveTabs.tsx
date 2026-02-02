/** Perspective tabs component */
import { useState, useEffect, useRef } from 'react'
import { Perspective, CustomWeights } from '../../api'
import { PERSPECTIVE_COLORS } from '../../utils'
import styles from './PerspectiveTabs.module.css'

interface PerspectiveTabsProps {
  perspectives: Perspective[]
  selected: string
  onSelect: (id: string) => void
  isAuthenticated?: boolean
  customWeights?: CustomWeights | null
  onCustomClick?: () => void
  onEditCustom?: () => void
}

export function PerspectiveTabs({
  perspectives,
  selected,
  onSelect,
  isAuthenticated = false,
  customWeights = null,
  onCustomClick,
  onEditCustom,
}: PerspectiveTabsProps) {
  const [showHelp, setShowHelp] = useState(false)
  const helpRef = useRef<HTMLDivElement>(null)

  // 枠外クリックでヘルプを閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (helpRef.current && !helpRef.current.contains(event.target as Node)) {
        setShowHelp(false)
      }
    }

    if (showHelp) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showHelp])

  return (
    <div className={styles.tabs}>
      {perspectives.map((p) => (
        <button
          key={p.id}
          className={`${styles.tab} ${selected === p.id ? styles.active : ''}`}
          onClick={() => onSelect(p.id)}
          style={
            {
              '--tab-color': PERSPECTIVE_COLORS[p.id] || '#64748b',
            } as React.CSSProperties
          }
        >
          {p.name}
        </button>
      ))}

      {/* カスタムボタン（ログイン時のみ） */}
      {isAuthenticated && onCustomClick && (
        <button
          className={`${styles.tab} ${selected === 'custom' ? styles.active : ''}`}
          onClick={onCustomClick}
          style={
            {
              '--tab-color': PERSPECTIVE_COLORS['custom'] || '#EC4899',
            } as React.CSSProperties
          }
        >
          カスタム
        </button>
      )}

      {/* ヘルプアイコン */}
      <div className={styles.helpWrapper} ref={helpRef}>
        <button
          className={styles.helpButton}
          onClick={() => setShowHelp(!showHelp)}
          aria-label="重みづけ比率を表示"
        >
          ?
        </button>

        {/* ツールチップ */}
        {showHelp && (
          <div className={styles.helpTooltip}>
            <div className={styles.helpHeader}>おすすめ銘柄の選び方</div>
            <p className={styles.helpDescription}>
              切り口ごとに評価の重みづけが異なります。
            </p>
            <table className={styles.helpTable}>
              <thead>
                <tr>
                  <th>切り口</th>
                  <th>配当</th>
                  <th>コスト</th>
                  <th>安定</th>
                  <th>規模</th>
                  <th>リターン</th>
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
                {isAuthenticated && (
                  <tr>
                    <td>カスタム</td>
                    <td>{customWeights?.dividend_power != null ? Math.round(customWeights.dividend_power * 100) : '--'}</td>
                    <td>{customWeights?.cost_efficiency != null ? Math.round(customWeights.cost_efficiency * 100) : '--'}</td>
                    <td>{customWeights?.scale_reliability != null ? Math.round(customWeights.scale_reliability * 100) : '--'}</td>
                    <td>{customWeights?.trading_quality != null ? Math.round(customWeights.trading_quality * 100) : '--'}</td>
                    <td>{customWeights?.return_performance != null ? Math.round(customWeights.return_performance * 100) : '--'}</td>
                  </tr>
                )}
              </tbody>
            </table>
            {isAuthenticated && onEditCustom && (
              <div className={styles.editLinkWrapper}>
                <button
                  className={styles.editLink}
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowHelp(false)
                    onEditCustom()
                  }}
                >
                  カスタムを編集
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
