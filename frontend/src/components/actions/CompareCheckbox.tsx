/** Compare checkbox component */
import styles from './CompareCheckbox.module.css'

interface CompareCheckboxProps {
  isInCompare: boolean
  onToggle: () => void
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function CompareCheckbox({
  isInCompare,
  onToggle,
  disabled = false,
  size = 'md',
}: CompareCheckboxProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!disabled) {
      onToggle()
    }
  }

  return (
    <button
      className={`${styles.checkbox} ${styles[size]} ${isInCompare ? styles.active : ''}`}
      onClick={handleClick}
      disabled={disabled}
      aria-label={isInCompare ? '比較から外す' : '比較に追加'}
      title={isInCompare ? '比較から外す' : '比較に追加'}
    >
      {isInCompare && (
        <svg
          className={styles.icon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      )}
    </button>
  )
}
