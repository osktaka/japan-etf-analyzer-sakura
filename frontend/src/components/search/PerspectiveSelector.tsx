/** Perspective selector component */
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
      {PERSPECTIVES.map(({ key, label }) => (
        <button
          key={key}
          className={`${styles.toggleButton} ${selectedPerspective === key ? styles.active : ''}`}
          onClick={() => onChange(key)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  )
}
