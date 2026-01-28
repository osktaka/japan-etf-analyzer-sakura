/** Favorite select modal component for adding favorites to compare list */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks'
import { favoritesApi } from '../../api/favorites'
import { getBatchPerformance } from '../../api/etf'
import { Favorite, BatchPerformanceData } from '../../api/types'
import { ROUTES } from '../../utils'
import { Loading } from '../common'
import { FavoriteButton } from '../favorite/FavoriteButton'
import { CompareCheckbox } from '../actions'
import styles from './FavoriteSelectModal.module.css'

interface FavoriteSelectModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (code: string) => void
  onRemove?: (code: string) => void
  existingCodes: string[]
}

export function FavoriteSelectModal({
  isOpen,
  onClose,
  onSelect,
  onRemove,
  existingCodes,
}: FavoriteSelectModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [removedCodes, setRemovedCodes] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [performance, setPerformance] = useState<BatchPerformanceData>({})

  const fetchFavorites = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await favoritesApi.getAll()
      setFavorites(data)
      setRemovedCodes(new Set())
      // パフォーマンスデータを取得
      if (data.length > 0) {
        const codes = data.map((f) => f.etf_code)
        const perfData = await getBatchPerformance(codes)
        setPerformance(perfData)
      }
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

  const handleFavoriteToggle = async (code: string) => {
    const isCurrentlyRemoved = removedCodes.has(code)
    if (isCurrentlyRemoved) {
      // 再度お気に入りに追加
      try {
        await favoritesApi.add(code)
        setRemovedCodes((prev) => {
          const next = new Set(prev)
          next.delete(code)
          return next
        })
      } catch {
        // エラー時は何もしない
      }
    } else {
      // お気に入りから削除
      try {
        await favoritesApi.remove(code)
        setRemovedCodes((prev) => new Set(prev).add(code))
      } catch {
        // エラー時は何もしない
      }
    }
  }

  const handleCheckboxChange = (code: string) => {
    if (existingCodes.includes(code)) {
      onRemove?.(code)
    } else {
      onSelect(code)
    }
  }

  const formatPerformance = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    const formatted = value.toFixed(1)
    return value >= 0 ? `+${formatted}%` : `${formatted}%`
  }

  const getPerformanceClass = (value: number | null | undefined) => {
    if (value === null || value === undefined) return ''
    return value >= 0 ? styles.positive : styles.negative
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
            <div className={styles.icon}>★</div>
            <h2 className={styles.title}>お気に入り銘柄</h2>
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
          <h2 className={styles.title}>お気に入り銘柄</h2>

          {isLoading && <Loading />}

          {error && <p className={styles.error}>{error}</p>}

          {!isLoading && !error && favorites.length === 0 && (
            <p className={styles.empty}>お気に入り銘柄がありません</p>
          )}

          {!isLoading && !error && favorites.length > 0 && (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.favoriteCol}></th>
                    <th>コード</th>
                    <th>銘柄名</th>
                    <th>カテゴリ</th>
                    <th className={styles.performanceCol}>1Y</th>
                    <th className={styles.compareCol}>比較</th>
                  </tr>
                </thead>
                <tbody>
                  {favorites.map((fav) => {
                    const isInList = existingCodes.includes(fav.etf_code)
                    const isRemoved = removedCodes.has(fav.etf_code)
                    const perf = performance[fav.etf_code]?.returns || {}
                    return (
                      <tr
                        key={fav.id}
                        className={isRemoved ? styles.removed : ''}
                      >
                        <td className={styles.favoriteCol}>
                          <FavoriteButton
                            isFavorite={!isRemoved}
                            onClick={() => handleFavoriteToggle(fav.etf_code)}
                            size="sm"
                          />
                        </td>
                        <td className={styles.code}>{fav.etf_code}</td>
                        <td className={styles.name}>{fav.etf.name}</td>
                        <td className={styles.category}>
                          {fav.etf.category || '-'}
                        </td>
                        <td
                          className={`${styles.performanceCol} ${getPerformanceClass(perf['1y'])}`}
                        >
                          {formatPerformance(perf['1y'])}
                        </td>
                        <td className={styles.compareCol}>
                          <CompareCheckbox
                            isInCompare={isInList}
                            onToggle={() => handleCheckboxChange(fav.etf_code)}
                            disabled={isRemoved}
                            size="sm"
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
