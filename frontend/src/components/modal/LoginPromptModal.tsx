/** Login prompt modal component */
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '../../utils'
import styles from './LoginPromptModal.module.css'

interface LoginPromptModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
}

export function LoginPromptModal({
  isOpen,
  onClose,
  title = '会員限定機能',
  description = 'この機能はログイン後にご利用いただけます。',
}: LoginPromptModalProps) {
  const navigate = useNavigate()

  if (!isOpen) return null

  const handleLogin = () => {
    onClose()
    navigate(ROUTES.LOGIN)
  }

  const handleRegister = () => {
    onClose()
    navigate(ROUTES.REGISTER)
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <div className={styles.icon}>&#9733;</div>
          <h2 className={styles.title}>{title}</h2>
          <p className={styles.description}>{description}</p>
          <div className={styles.buttons}>
            <button className="btn btn-primary" onClick={handleLogin}>
              ログイン
            </button>
            <button className="btn btn-secondary" onClick={handleRegister}>
              新規登録
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
