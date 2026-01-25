/** Perspective tabs component */
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
    </div>
  )
}
