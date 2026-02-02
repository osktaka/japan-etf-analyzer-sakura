/** Perspective tabs component */
import { useState, useEffect, useRef } from 'react'
import { Perspective } from '../../api'
import { PERSPECTIVE_COLORS } from '../../utils'
import styles from './PerspectiveTabs.module.css'

interface PerspectiveTabsProps {
  perspectives: Perspective[]
  selected: string
  onSelect: (id: string) => void
}

export function PerspectiveTabs({
  perspectives,
  selected,
  onSelect,
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
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
