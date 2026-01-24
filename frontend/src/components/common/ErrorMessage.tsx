/** Error message component */
import styles from './ErrorMessage.module.css';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className={styles.container}>
      <div className={styles.icon}>!</div>
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <button className={`btn btn-secondary ${styles.button}`} onClick={onRetry}>
          再試行
        </button>
      )}
    </div>
  );
}
