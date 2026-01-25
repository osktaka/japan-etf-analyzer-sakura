/** Compare button component */
import styles from './CompareButton.module.css'

interface CompareButtonProps {
  isInCompare: boolean
  onToggle: () => void
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  iconOnly?: boolean
}

export function CompareButton({
  isInCompare,
  onToggle,
  disabled = false,
  size = 'md',
  iconOnly = false,
}: CompareButtonProps) {
  const sizeClass = size !== 'md' ? styles[size] : ''

  return (
    <button
      className={`${styles.button} ${isInCompare ? styles.active : ''} ${sizeClass} ${
        iconOnly ? styles.iconOnly : ''
      }`}
      onClick={onToggle}
      disabled={disabled}
      aria-label={isInCompare ? '比較から外す' : '比較に追加'}
    >
      <span className={styles.icon}>{isInCompare ? '✓' : '+'}</span>
      {!iconOnly && (
        <span className={styles.label}>
          {isInCompare ? '比較中' : '比較に追加'}
        </span>
      )}
    </button>
  )
}
