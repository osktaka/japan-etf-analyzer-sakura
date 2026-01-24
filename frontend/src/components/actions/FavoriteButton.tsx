/** Favorite button component */
import styles from './FavoriteButton.module.css';

interface FavoriteButtonProps {
  isFavorite: boolean;
  onToggle: () => void;
  onLoginRequired?: () => void;
  isLoggedIn?: boolean;
  size?: 'sm' | 'md' | 'lg';
  iconOnly?: boolean;
  disabled?: boolean;
}

export function FavoriteButton({
  isFavorite,
  onToggle,
  onLoginRequired,
  isLoggedIn = false,
  size = 'md',
  iconOnly = false,
  disabled = false,
}: FavoriteButtonProps) {
  const handleClick = () => {
    if (!isLoggedIn && onLoginRequired) {
      onLoginRequired();
      return;
    }
    onToggle();
  };

  const sizeClass = size !== 'md' ? styles[size] : '';

  return (
    <button
      className={`${styles.button} ${isFavorite ? styles.active : ''} ${sizeClass} ${
        iconOnly ? styles.iconOnly : ''
      }`}
      onClick={handleClick}
      disabled={disabled}
      aria-label={isFavorite ? 'お気に入りから削除' : 'お気に入りに追加'}
    >
      <span className={styles.icon}>{isFavorite ? '★' : '☆'}</span>
      {!iconOnly && (
        <span className={styles.label}>
          {isFavorite ? 'お気に入り済み' : 'お気に入り'}
        </span>
      )}
    </button>
  );
}
