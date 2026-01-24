/** Login prompt modal component */
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../utils';
import styles from './LoginPromptModal.module.css';

interface LoginPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LoginPromptModal({ isOpen, onClose }: LoginPromptModalProps) {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleLogin = () => {
    onClose();
    navigate(ROUTES.LOGIN);
  };

  const handleRegister = () => {
    onClose();
    navigate(ROUTES.REGISTER);
  };

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
          <div className={styles.buttons}>
            <button className="btn btn-primary" onClick={handleLogin}>
              ログイン
            </button>
            <button className="btn btn-secondary" onClick={handleRegister}>
              新規登録
            </button>
          </div>
          <button className={styles.closeLink} onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}
