/** Favorite button component */
import styles from './FavoriteButton.module.css'

interface FavoriteButtonProps {
  isFavorite: boolean
  onClick: () => void
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
}

export function FavoriteButton({
  isFavorite,
  onClick,
  size = 'md',
  disabled = false,
}: FavoriteButtonProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!disabled) {
      onClick()
    }
  }

  return (
    <button
      className={`${styles.button} ${styles[size]} ${isFavorite ? styles.active : ''}`}
      onClick={handleClick}
      disabled={disabled}
      aria-label={isFavorite ? 'お気に入りから削除' : 'お気に入りに追加'}
      title={isFavorite ? 'お気に入りから削除' : 'お気に入りに追加'}
    >
      <svg
        className={styles.icon}
        viewBox="0 0 24 24"
        fill={isFavorite ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
      </svg>
    </button>
  )
}
