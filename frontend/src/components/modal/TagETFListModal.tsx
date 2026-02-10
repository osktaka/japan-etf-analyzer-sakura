/** Tag ETF list modal - displays ETFs filtered by a specific tag */
import { useState, useEffect, useMemo } from 'react'
import { searchETFs } from '../../api/etf'
import { ETFSummary } from '../../api/types'
import { userSettingsApi } from '../../api/userSettings'
import type { CustomWeights } from '../../api/types'
import { useAuth, useFavorites, usePortfolio } from '../../hooks'
import { MomentumBadge } from '../common/MomentumBadge'
import { FavoriteButton } from '../favorite/FavoriteButton'
import { ETFDetailModal } from './ETFDetailModal'
import { CustomWeightsPromptModal } from './CustomWeightsPromptModal'
import { WeightsHelpModal } from './WeightsHelpModal'
import { Loading } from '../common'
import { MOMENTUM_SCORES, MomentumLabel } from '../../utils/momentum'
import { PerspectiveSelector } from '../search/PerspectiveSelector'
import type { PerspectiveKey } from '../search/ETFTableView'
import { PERSPECTIVE_COLORS } from '../../utils'
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

  const [selectedPerspective, setSelectedPerspective] =
    useState<PerspectiveKey>(() => {
      const stored = localStorage.getItem('etf-perspective')
      const valid = [
        'balance',
        'dividend',
        'low-cost',
        'stability',
        'volume',
        'growth',
        'custom',
      ]
      if (stored && valid.includes(stored)) {
        if (stored === 'custom' && !isAuthenticated) return 'balance'
        return stored as PerspectiveKey
      }
      return 'balance'
    })

  const [customWeights, setCustomWeights] = useState<CustomWeights | null>(null)
  const [showCustomWeightsPromptModal, setShowCustomWeightsPromptModal] =
    useState(false)
  const [showWeightsHelpModal, setShowWeightsHelpModal] = useState(false)

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  const sortedEtfs = useMemo(() => {
    return [...etfs].sort((a, b) => {
      const momentumA =
        a.momentum_label && a.momentum_label in MOMENTUM_SCORES
          ? MOMENTUM_SCORES[a.momentum_label as MomentumLabel]
          : -1
      const momentumB =
        b.momentum_label && b.momentum_label in MOMENTUM_SCORES
          ? MOMENTUM_SCORES[b.momentum_label as MomentumLabel]
          : -1
      if (momentumA !== momentumB) return momentumB - momentumA
      // 第2キー: 評価スコア降順
      const scoreA = a.score ?? -1
      const scoreB = b.score ?? -1
      if (scoreA !== scoreB) return scoreB - scoreA
      return a.code.localeCompare(b.code)
    })
  }, [etfs])

  const handlePerspectiveChange = (perspective: PerspectiveKey) => {
    setSelectedPerspective(perspective)
    localStorage.setItem('etf-perspective', perspective)
  }

  useEffect(() => {
    if (!isAuthenticated || !isOpen) return
    const fetchCustomWeights = async () => {
      try {
        const settings = await userSettingsApi.getSettings()
        setCustomWeights(settings.custom_weights)
      } catch {
        // エラー時は無視（カスタム機能が使えないだけ）
      }
    }
    fetchCustomWeights()
  }, [isAuthenticated, isOpen])

  const handleCustomClick = () => {
    if (!customWeights) {
      setShowCustomWeightsPromptModal(true)
    } else {
      handlePerspectiveChange('custom')
    }
  }

  useEffect(() => {
    if (!isOpen) return

    const fetchETFs = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const result = await searchETFs({
          tag_ids: [tagId],
          limit: 200,
          perspective: selectedPerspective,
          ...(selectedPerspective === 'custom' && customWeights
            ? { custom_weights: JSON.stringify(customWeights) }
            : {}),
        })
        setEtfs(result.items)
      } catch {
        setError('銘柄の取得に失敗しました')
      } finally {
        setIsLoading(false)
      }
    }

    fetchETFs()
  }, [isOpen, tagId, selectedPerspective, customWeights])

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

          <PerspectiveSelector
            selectedPerspective={selectedPerspective}
            onChange={handlePerspectiveChange}
            className={styles.perspectiveSelector}
            isAuthenticated={isAuthenticated}
            customWeights={customWeights}
            onCustomClick={isAuthenticated ? handleCustomClick : undefined}
            onHelpClick={() => setShowWeightsHelpModal(true)}
          />

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
                      <th className={styles.scoreCol}>スコア</th>
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
                        <td className={styles.scoreCol}>
                          {etf.score != null ? (
                            <span
                              style={{
                                color:
                                  PERSPECTIVE_COLORS[selectedPerspective],
                              }}
                            >
                              {etf.score.toFixed(1)}
                            </span>
                          ) : (
                            <span className={styles.noScore}>-</span>
                          )}
                        </td>
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

        <CustomWeightsPromptModal
          isOpen={showCustomWeightsPromptModal}
          onClose={() => setShowCustomWeightsPromptModal(false)}
          onRegister={() => setShowCustomWeightsPromptModal(false)}
        />

        <WeightsHelpModal
          isOpen={showWeightsHelpModal}
          onClose={() => setShowWeightsHelpModal(false)}
          isAuthenticated={isAuthenticated}
          customWeights={customWeights}
        />
      </div>
    </div>
  )
}
