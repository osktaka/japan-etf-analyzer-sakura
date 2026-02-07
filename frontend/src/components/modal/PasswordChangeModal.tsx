/** Password change modal component */
import { useState } from 'react'
import { authApi } from '../../api/auth'
import styles from './PasswordChangeModal.module.css'

interface PasswordChangeModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PasswordChangeModal({
  isOpen,
  onClose,
}: PasswordChangeModalProps) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen) return null

  const resetForm = () => {
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // バリデーション: 8文字以上
    if (newPassword.length < 8) {
      setError('新しいパスワードは8文字以上で入力してください')
      return
    }

    // バリデーション: 確認パスワード一致
    if (newPassword !== confirmPassword) {
      setError('新しいパスワードと確認パスワードが一致しません')
      return
    }

    setIsSubmitting(true)
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      alert('パスワードを変更しました')
      handleClose()
    } catch {
      setError(
        'パスワードの変更に失敗しました。現在のパスワードをご確認ください。'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={handleClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>パスワード変更</h2>
          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <label htmlFor="currentPassword" className={styles.label}>
                現在のパスワード
              </label>
              <input
                type="password"
                id="currentPassword"
                className={styles.input}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="newPassword" className={styles.label}>
                新しいパスワード
              </label>
              <input
                type="password"
                id="newPassword"
                className={styles.input}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
              <span className={styles.hint}>8文字以上</span>
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="confirmPassword" className={styles.label}>
                新しいパスワード（確認）
              </label>
              <input
                type="password"
                id="confirmPassword"
                className={styles.input}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
            {error && <div className={styles.error}>{error}</div>}
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.cancelBtn}
                onClick={handleClose}
              >
                キャンセル
              </button>
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting}
              >
                {isSubmitting ? '変更中...' : '変更する'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
