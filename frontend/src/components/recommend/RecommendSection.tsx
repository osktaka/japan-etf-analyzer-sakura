/** Recommend section component */
import { useState, useEffect } from 'react'
import { getPerspectives, Perspective, CustomWeights } from '../../api'
import { useRecommendations } from '../../hooks'
import { Loading, ErrorMessage } from '../common'
import { ETFCard } from '../etf'
import { WeightsHelpModal } from '../modal'
import { PerspectiveTabs } from './PerspectiveTabs'
import styles from './RecommendSection.module.css'

interface RecommendSectionProps {
  onETFClick: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  isFavorite?: (code: string) => boolean
  onFavoriteToggle?: (code: string) => void
  onShowAll?: () => void
  selectedPerspective?: string
  onSelectPerspective?: (perspective: string) => void
  isAuthenticated?: boolean
  customWeights?: CustomWeights | null
  onCustomClick?: () => void
  onEditCustom?: () => void
}

export function RecommendSection({
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
  onShowAll,
  selectedPerspective,
  onSelectPerspective,
  isAuthenticated = false,
  customWeights = null,
  onCustomClick,
  onEditCustom,
}: RecommendSectionProps) {
  const [perspectives, setPerspectives] = useState<Perspective[]>([])
  // 制御/非制御ハイブリッド: propsがあれば使用、なければ内部state（既存互換）
  const [internalSelected, setInternalSelected] = useState('balance')
  const [showWeightsHelp, setShowWeightsHelp] = useState(false)

  const selected = selectedPerspective ?? internalSelected
  const handleSelect = (p: string) => {
    if (onSelectPerspective) {
      onSelectPerspective(p)
    } else {
      setInternalSelected(p)
    }
  }

  const { data, isLoading, error } = useRecommendations(selected, 'full')

  useEffect(() => {
    getPerspectives().then(setPerspectives)
  }, [])

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>おすすめ銘柄</h2>
      {perspectives.length > 0 && (
        <PerspectiveTabs
          perspectives={perspectives}
          selected={selected}
          onSelect={handleSelect}
          onCustomClick={onCustomClick}
          onHelpClick={() => setShowWeightsHelp(true)}
        />
      )}
      {data && (
        <p className={styles.description}>{data.perspective.description}</p>
      )}
      {isLoading && <Loading />}
      {error && <ErrorMessage message="データの取得に失敗しました" />}
      {data && (
        <div className={styles.grid}>
          {data.items.map((etf) => (
            <ETFCard
              key={etf.code}
              etf={etf}
              onClick={() => onETFClick(etf.code)}
              isSelected={isInCompare?.(etf.code)}
              showCompareButton={!!onCompareToggle}
              onCompareToggle={() => onCompareToggle?.(etf.code)}
              isFavorite={isFavorite?.(etf.code)}
              onFavoriteToggle={
                onFavoriteToggle ? () => onFavoriteToggle(etf.code) : undefined
              }
              perspective={selected}
            />
          ))}
        </div>
      )}
      {onShowAll && (
        <div className={styles.showAllWrapper}>
          <button
            type="button"
            className={styles.showAllLink}
            onClick={onShowAll}
          >
            もっと見る →
          </button>
        </div>
      )}

      <WeightsHelpModal
        isOpen={showWeightsHelp}
        onClose={() => setShowWeightsHelp(false)}
        isAuthenticated={isAuthenticated}
        customWeights={customWeights}
        onEditCustom={onEditCustom}
      />
    </section>
  )
}
