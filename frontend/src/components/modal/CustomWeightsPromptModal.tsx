/** Custom weights prompt modal component */
import styles from './LoginPromptModal.module.css'

interface CustomWeightsPromptModalProps {
  isOpen: boolean
  onClose: () => void
  onRegister: () => void
}

export function CustomWeightsPromptModal({
  isOpen,
  onClose,
  onRegister,
}: CustomWeightsPromptModalProps) {
  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <div className={styles.icon}>⚙️</div>
          <h2 className={styles.title}>カスタム重みづけ未設定</h2>
          <p className={styles.description}>
            カスタム重みづけを設定すると、5軸の評価比率をカスタマイズできます。
          </p>
          <div className={styles.buttons}>
            <button className="btn btn-primary" onClick={onRegister}>
              設定する
            </button>
          </div>
          <button className={styles.closeLink} onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  )
}
