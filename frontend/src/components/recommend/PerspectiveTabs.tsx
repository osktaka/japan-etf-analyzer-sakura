/** Perspective tabs component */
import { Perspective } from '../../api'
import { PERSPECTIVE_COLORS } from '../../utils'
import styles from './PerspectiveTabs.module.css'

interface PerspectiveTabsProps {
  perspectives: Perspective[]
  selected: string
  onSelect: (id: string) => void
  onCustomClick?: () => void
  onHelpClick?: () => void
}

export function PerspectiveTabs({
  perspectives,
  selected,
  onSelect,
  onCustomClick,
  onHelpClick,
}: PerspectiveTabsProps) {
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

      {/* カスタムボタン */}
      {onCustomClick && (
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
      {onHelpClick && (
        <div className={styles.helpWrapper}>
          <button
            className={styles.helpButton}
            onClick={() => onHelpClick()}
            aria-label="重みづけ比率を表示"
          >
            ?
          </button>
        </div>
      )}
    </div>
  )
}
