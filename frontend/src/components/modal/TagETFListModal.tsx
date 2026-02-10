/** Tag ETF list modal - displays ETFs filtered by a specific tag */
import { useState, useEffect, useMemo } from 'react'
import { searchETFs } from '../../api/etf'
import { ETFSummary } from '../../api/types'
import { useAuth, useFavorites, usePortfolio } from '../../hooks'
import { MomentumBadge } from '../common/MomentumBadge'
import { FavoriteButton } from '../favorite/FavoriteButton'
import { ETFDetailModal } from './ETFDetailModal'
import { Loading } from '../common'
import { MOMENTUM_SCORES, MomentumLabel } from '../../utils/momentum'
import styles from './TagETFListModal.module.css'

interface TagETFListModalProps {
  isOpen: boolean
  onClose: () => void
  tagId: number
  tagName: string
}

export function TagETFListModal({
  isOpen,
  onClose,
  tagId,
  tagName,
}: TagETFListModalProps) {
  const { isAuthenticated } = useAuth()
  const { favoriteCodes, toggleFavorite } = useFavorites()
  const { holdings } = usePortfolio()

  const [etfs, setEtfs] = useState<ETFSummary[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  // Sort by momentum score descending, then code ascending
  const sortedEtfs = useMemo(() => {
    return [...etfs].sort((a, b) => {
      const scoreA =
        a.momentum_label && a.momentum_label in MOMENTUM_SCORES
          ? MOMENTUM_SCORES[a.momentum_label as MomentumLabel]
          : -1
      const scoreB =
        b.momentum_label && b.momentum_label in MOMENTUM_SCORES
          ? MOMENTUM_SCORES[b.momentum_label as MomentumLabel]
          : -1
      if (scoreA !== scoreB) return scoreB - scoreA
      return a.code.localeCompare(b.code)
    })
  }, [etfs])

  useEffect(() => {
    if (!isOpen) return

    const fetchETFs = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const result = await searchETFs({ tag_ids: [tagId], limit: 200 })
        setEtfs(result.items)
      } catch {
        setError('銘柄の取得に失敗しました')
      } finally {
        setIsLoading(false)
      }
    }

    fetchETFs()
  }, [isOpen, tagId])

  if (!isOpen) return null

  const handleFavoriteToggle = (code: string) => {
    toggleFavorite(code)
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>#{tagName}</h2>

          {isLoading && <Loading />}

          {error && <p className={styles.error}>{error}</p>}

          {!isLoading && !error && sortedEtfs.length === 0 && (
            <p className={styles.empty}>該当する銘柄がありません</p>
          )}

          {!isLoading && !error && sortedEtfs.length > 0 && (
            <>
              <p className={styles.count}>{sortedEtfs.length}件</p>
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.momentumCol}>勢い</th>
                      {isAuthenticated && (
                        <th className={styles.favoriteCol}></th>
                      )}
                      <th>コード</th>
                      <th>銘柄名</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedEtfs.map((etf) => (
                      <tr
                        key={etf.code}
                        onClick={() => setSelectedCode(etf.code)}
                      >
                        <td className={styles.momentumCol}>
                          <MomentumBadge
                            label={etf.momentum_label}
                            size="sm"
                          />
                        </td>
                        {isAuthenticated && (
                          <td
                            className={styles.favoriteCol}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <FavoriteButton
                              isFavorite={favoriteCodes.has(etf.code)}
                              onClick={() => handleFavoriteToggle(etf.code)}
                              size="sm"
                              isHolding={holdingCodes.has(etf.code)}
                            />
                          </td>
                        )}
                        <td className={styles.code}>{etf.code}</td>
                        <td className={styles.name}>{etf.name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <ETFDetailModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
          isFavorite={selectedCode ? favoriteCodes.has(selectedCode) : false}
          onFavoriteToggle={() => {
            if (selectedCode) toggleFavorite(selectedCode)
          }}
        />
      </div>
    </div>
  )
}
