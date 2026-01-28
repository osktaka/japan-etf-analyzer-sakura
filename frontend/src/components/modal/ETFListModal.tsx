/** ETF list modal component for displaying favorites or compare list */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, usePortfolio } from '../../hooks'
import { favoritesApi } from '../../api/favorites'
import { getBatchPerformance } from '../../api/etf'
import { Favorite, BatchPerformanceData, ETFDetail } from '../../api/types'
import { ROUTES } from '../../utils'
import { Loading } from '../common'
import { FavoriteButton } from '../favorite/FavoriteButton'
import { CompareCheckbox } from '../actions'
import { ETFDetailModal } from './ETFDetailModal'
import styles from './ETFListModal.module.css'

interface ETFListModalProps {
  isOpen: boolean
  onClose: () => void
  mode: 'favorite' | 'compare'
  // favoriteモード用
  onSelect?: (code: string) => void
  onRemove?: (code: string) => void
  existingCodes?: string[]
  // compareモード用
  etfs?: ETFDetail[]
}

export function ETFListModal({
  isOpen,
  onClose,
  mode,
  onSelect,
  onRemove,
  existingCodes = [],
  etfs = [],
}: ETFListModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { holdings } = usePortfolio()
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [compareEtfs, setCompareEtfs] = useState<ETFDetail[]>([]) // compareモード用の表示リスト
  const [removedCodes, setRemovedCodes] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [performance, setPerformance] = useState<BatchPerformanceData>({})
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

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

  // compareモード用: propsのetfsからパフォーマンスデータを取得
  const fetchComparePerformance = useCallback(async () => {
    if (etfs.length === 0) {
      setPerformance({})
      return
    }
    setIsLoading(true)
    try {
      const codes = etfs.map((e) => e.code)
      const perfData = await getBatchPerformance(codes)
      setPerformance(perfData)
    } catch {
      setPerformance({})
    } finally {
      setIsLoading(false)
    }
  }, [etfs])

  // お気に入り状態の取得（両モードで必要）
  useEffect(() => {
    if (!isOpen || !isAuthenticated) return
    fetchFavorites()
  }, [isOpen, isAuthenticated, fetchFavorites])

  // compareモード用: モーダル開いたときに表示リストをコピー＆パフォーマンス取得
  useEffect(() => {
    if (!isOpen || mode !== 'compare') return
    setCompareEtfs(etfs)
    fetchComparePerformance()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, mode])

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
    const isInFavorites = favorites.some((f) => f.etf_code === code)
    const isCurrentlyRemoved = removedCodes.has(code)

    if (isInFavorites && !isCurrentlyRemoved) {
      // お気に入りから削除
      try {
        await favoritesApi.remove(code)
        setRemovedCodes((prev) => new Set(prev).add(code))
      } catch {
        // エラー時は何もしない
      }
    } else {
      // お気に入りに追加（復帰または新規追加）
      try {
        await favoritesApi.add(code)
        if (isCurrentlyRemoved) {
          setRemovedCodes((prev) => {
            const next = new Set(prev)
            next.delete(code)
            return next
          })
        } else {
          // 新規追加の場合はfavoritesを再取得
          const data = await favoritesApi.getAll()
          setFavorites(data)
        }
      } catch {
        // エラー時は何もしない
      }
    }
  }

  const handleCheckboxChange = (code: string) => {
    // 両モード共通: トグル動作
    if (existingCodes.includes(code)) {
      onRemove?.(code)
    } else {
      onSelect?.(code)
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

  // 未ログイン時はログイン促進表示（favoriteモードのみ）
  if (mode === 'favorite' && !isAuthenticated) {
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

  // compareモード用のデータ
  const displayItems =
    mode === 'compare'
      ? compareEtfs.map((etf) => ({
          key: etf.code,
          code: etf.code,
          name: etf.name,
          category: etf.category?.name || '-',
        }))
      : favorites.map((fav) => ({
          key: String(fav.id),
          code: fav.etf_code,
          name: fav.etf.name,
          category: fav.etf.category || '-',
        }))

  const emptyMessage =
    mode === 'compare' ? '比較銘柄がありません' : 'お気に入り銘柄がありません'
  const modalTitle =
    mode === 'compare' ? '比較銘柄リスト' : 'お気に入り銘柄'

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>{modalTitle}</h2>

          {isLoading && <Loading />}

          {error && <p className={styles.error}>{error}</p>}

          {!isLoading && !error && displayItems.length === 0 && (
            <p className={styles.empty}>{emptyMessage}</p>
          )}

          {!isLoading && !error && displayItems.length > 0 && (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {isAuthenticated && (
                      <th className={styles.favoriteCol}></th>
                    )}
                    <th>コード</th>
                    <th>銘柄名</th>
                    <th>カテゴリ</th>
                    <th className={styles.performanceCol}>1Y</th>
                    <th className={styles.compareCol}>
                      比較
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {displayItems.map((item) => {
                    const isInList = existingCodes.includes(item.code)
                    const isRemoved = removedCodes.has(item.code)
                    const perf = performance[item.code]?.returns || {}
                    // お気に入り状態: favoriteモードはremovedで判定、compareモードはfavoritesリストで判定
                    const isFavorite =
                      mode === 'favorite'
                        ? !isRemoved
                        : favorites.some((f) => f.etf_code === item.code) &&
                          !isRemoved
                    return (
                      <tr
                        key={item.key}
                        className={
                          mode === 'favorite' && isRemoved ? styles.removed : ''
                        }
                        onClick={() => setSelectedCode(item.code)}
                        style={{ cursor: 'pointer' }}
                      >
                        {isAuthenticated && (
                          <td
                            className={styles.favoriteCol}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <FavoriteButton
                              isFavorite={isFavorite}
                              onClick={() => handleFavoriteToggle(item.code)}
                              size="sm"
                              isHolding={holdingCodes.has(item.code)}
                            />
                          </td>
                        )}
                        <td className={styles.code}>{item.code}</td>
                        <td className={styles.name}>{item.name}</td>
                        <td className={styles.category}>{item.category}</td>
                        <td
                          className={`${styles.performanceCol} ${getPerformanceClass(perf['1y'])}`}
                        >
                          {formatPerformance(perf['1y'])}
                        </td>
                        <td
                          className={styles.compareCol}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <CompareCheckbox
                            isInCompare={isInList}
                            onToggle={() => handleCheckboxChange(item.code)}
                            disabled={mode === 'favorite' && isRemoved}
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

        <ETFDetailModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
          isInCompare={selectedCode ? existingCodes.includes(selectedCode) : false}
          onCompareToggle={() => {
            if (selectedCode) {
              handleCheckboxChange(selectedCode)
            }
          }}
        />
      </div>
    </div>
  )
}
