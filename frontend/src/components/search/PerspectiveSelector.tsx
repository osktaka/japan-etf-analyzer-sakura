/** Perspective selector component */
import { PERSPECTIVE_COLORS } from '../../utils'
import styles from '../../pages/TopPage.module.css'
import helpStyles from '../recommend/PerspectiveTabs.module.css'
import type { PerspectiveKey } from './ETFTableView'
import type { CustomWeights } from '../../api'

interface PerspectiveSelectorProps {
  selectedPerspective: PerspectiveKey
  onChange: (perspective: PerspectiveKey) => void
  className?: string
  isAuthenticated?: boolean
  customWeights?: CustomWeights | null
  onCustomClick?: () => void
  onHelpClick?: () => void
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
  onCustomClick,
  onHelpClick,
}: PerspectiveSelectorProps) {
  return (
    <div className={className || styles.scoringModeToggle}>
      {PERSPECTIVES.map(({ key, label }) => {
        const isActive = selectedPerspective === key
        const activeColor =
          PERSPECTIVE_COLORS[key] || PERSPECTIVE_COLORS.balance
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

      {/* カスタムボタン */}
      {onCustomClick && (
        <button
          className={`${styles.toggleButton} ${selectedPerspective === 'custom' ? styles.active : ''}`}
          onClick={onCustomClick}
          type="button"
          style={
            selectedPerspective === 'custom'
              ? {
                  backgroundColor: PERSPECTIVE_COLORS['custom'] || '#EC4899',
                  borderColor: PERSPECTIVE_COLORS['custom'] || '#EC4899',
                  color: 'white',
                }
              : undefined
          }
        >
          カスタム
        </button>
      )}

      {/* ヘルプアイコン */}
      {onHelpClick && (
        <div className={helpStyles.helpWrapper}>
          <button
            className={helpStyles.helpButton}
            onClick={onHelpClick}
            aria-label="重みづけ比率を表示"
            type="button"
          >
            ?
          </button>
        </div>
      )}
    </div>
  )
}
