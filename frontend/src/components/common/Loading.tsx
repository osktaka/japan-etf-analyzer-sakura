/** Loading spinner component */
import styles from './Loading.module.css';

interface LoadingProps {
  message?: string;
}

export function Loading({ message = '読み込み中...' }: LoadingProps) {
  return (
    <div className={styles.container}>
      <div className={styles.spinner} />
      <p className={styles.message}>{message}</p>
    </div>
  );
}
