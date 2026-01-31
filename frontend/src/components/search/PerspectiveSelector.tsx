/** Perspective selector component */
import { PERSPECTIVE_COLORS } from '../../utils'
import styles from '../../pages/TopPage.module.css'
import type { PerspectiveKey } from './ETFTableView'

interface PerspectiveSelectorProps {
  selectedPerspective: PerspectiveKey
  onChange: (perspective: PerspectiveKey) => void
  className?: string
}

const PERSPECTIVES: { key: PerspectiveKey; label: string }[] = [
  { key: 'balance', label: 'バランス' },
  { key: 'dividend', label: '配当収入' },
  { key: 'low-cost', label: '低コスト' },
  { key: 'stability', label: '安定性' },
  { key: 'volume', label: '取引規模' },
  { key: 'growth', label: '成長性' },
]

export function PerspectiveSelector({
  selectedPerspective,
  onChange,
  className,
}: PerspectiveSelectorProps) {
  return (
    <div className={className || styles.scoringModeToggle}>
      {PERSPECTIVES.map(({ key, label }) => {
        const isActive = selectedPerspective === key
        const activeColor = PERSPECTIVE_COLORS[key] || PERSPECTIVE_COLORS.balance
        return (
          <button
            key={key}
            className={`${styles.toggleButton} ${isActive ? styles.active : ''}`}
            onClick={() => onChange(key)}
            type="button"
            style={
              isActive
                ? {
                    backgroundColor: activeColor,
                    borderColor: activeColor,
                    color: 'white',
                  }
                : undefined
            }
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
