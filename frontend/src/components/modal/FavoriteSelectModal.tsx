/** Favorite select modal component for adding favorites to compare list */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks'
import { favoritesApi } from '../../api/favorites'
import { Favorite } from '../../api/types'
import { ROUTES } from '../../utils'
import { Loading } from '../common'
import styles from './FavoriteSelectModal.module.css'

interface FavoriteSelectModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (code: string) => void
  existingCodes: string[]
}

export function FavoriteSelectModal({
  isOpen,
  onClose,
  onSelect,
  existingCodes,
}: FavoriteSelectModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchFavorites = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await favoritesApi.getAll()
      setFavorites(data)
    } catch {
      setError('お気に入りの取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      fetchFavorites()
    }
  }, [isOpen, isAuthenticated, fetchFavorites])

  if (!isOpen) return null

  const handleLogin = () => {
    onClose()
    navigate(ROUTES.LOGIN)
  }

  const handleRegister = () => {
    onClose()
    navigate(ROUTES.REGISTER)
  }

  const handleSelect = (code: string) => {
    onSelect(code)
  }

  // 未ログイン時はログイン促進表示
  if (!isAuthenticated) {
    return (
      <div className={styles.overlay} onClick={onClose}>
        <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
          <div className={styles.content}>
            <div className={styles.icon}>&#9829;</div>
            <h2 className={styles.title}>お気に入りから追加</h2>
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
    )
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>お気に入りから追加</h2>
          <p className={styles.description}>
            比較リストに追加する銘柄を選択してください
          </p>

          {isLoading && <Loading />}

          {error && <p className={styles.error}>{error}</p>}

          {!isLoading && !error && favorites.length === 0 && (
            <p className={styles.empty}>お気に入り銘柄がありません</p>
          )}

          {!isLoading && !error && favorites.length > 0 && (
            <div className={styles.list}>
              {favorites.map((fav) => {
                const isInList = existingCodes.includes(fav.etf_code)
                return (
                  <button
                    key={fav.id}
                    className={`${styles.item} ${isInList ? styles.disabled : ''}`}
                    onClick={() => !isInList && handleSelect(fav.etf_code)}
                    disabled={isInList}
                  >
                    <span className={styles.code}>{fav.etf_code}</span>
                    <span className={styles.name}>{fav.etf.name}</span>
                    {isInList && <span className={styles.badge}>追加済み</span>}
                  </button>
                )
              })}
            </div>
          )}

          <button className={styles.closeLink} onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  )
}
