/** Scoring mode toggle component */
import styles from '../../pages/TopPage.module.css'

export type ScoringMode = 'full' | 'partial'

interface ScoringModeToggleProps {
  scoringMode: ScoringMode
  onChange: (mode: ScoringMode) => void
  className?: string
}

export function ScoringModeToggle({
  scoringMode,
  onChange,
  className,
}: ScoringModeToggleProps) {
  return (
    <div className={className || styles.scoringModeToggle}>
      <button
        className={`${styles.toggleButton} ${scoringMode === 'full' ? styles.active : ''}`}
        onClick={() => onChange('full')}
        type="button"
      >
        総合評価
      </button>
      <button
        className={`${styles.toggleButton} ${scoringMode === 'partial' ? styles.active : ''}`}
        onClick={() => onChange('partial')}
        type="button"
      >
        軸別評価
      </button>
    </div>
  )
}
