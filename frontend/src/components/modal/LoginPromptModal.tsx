/** Login prompt modal component */
import styles from './LoginPromptModal.module.css';

interface LoginPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LoginPromptModal({ isOpen, onClose }: LoginPromptModalProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <div className={styles.icon}>&#9829;</div>
          <h2 className={styles.title}>お気に入り機能</h2>
          <p className={styles.description}>
            お気に入り機能はログイン後にご利用いただけます。
          </p>
          <p className={styles.note}>
            ※ ログイン機能は今後のアップデートで追加予定です
          </p>
          <button className="btn btn-primary" onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}
