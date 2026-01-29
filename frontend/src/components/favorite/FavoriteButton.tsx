/** Favorite button component */
import styles from './FavoriteButton.module.css'

interface FavoriteButtonProps {
  isFavorite: boolean
  onClick: () => void
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  isHolding?: boolean
}

export function FavoriteButton({
  isFavorite,
  onClick,
  size = 'md',
  disabled = false,
  isHolding = false,
}: FavoriteButtonProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!disabled) {
      onClick()
    }
  }

  return (
    <button
      className={`${styles.button} ${styles[size]} ${isFavorite ? styles.active : ''} ${isHolding ? styles.holding : ''}`}
      onClick={handleClick}
      disabled={disabled}
      aria-label={isFavorite ? 'お気に入りから削除' : 'お気に入りに追加'}
      title={
        isHolding
          ? '保有中'
          : isFavorite
            ? 'お気に入りから削除'
            : 'お気に入りに追加'
      }
    >
      <svg
        className={styles.icon}
        viewBox="0 0 24 24"
        fill={isFavorite ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    </button>
  )
}
