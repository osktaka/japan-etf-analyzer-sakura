/** Recommend section component */
import { useState, useEffect } from 'react'
import { getPerspectives, Perspective } from '../../api'
import { useRecommendations } from '../../hooks'
import { Loading, ErrorMessage } from '../common'
import { ETFCard } from '../etf'
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
}: RecommendSectionProps) {
  const [perspectives, setPerspectives] = useState<Perspective[]>([])
  // 制御/非制御ハイブリッド: propsがあれば使用、なければ内部state（既存互換）
  const [internalSelected, setInternalSelected] = useState('balance')
  const [scoringMode, setScoringMode] = useState<'full' | 'partial'>(() => {
    const saved = localStorage.getItem('scoringMode')
    return (saved === 'partial' ? 'partial' : 'full') as 'full' | 'partial'
  })

  const selected = selectedPerspective ?? internalSelected
  const handleSelect = (p: string) => {
    if (onSelectPerspective) {
      onSelectPerspective(p)
    } else {
      setInternalSelected(p)
    }
  }

  const handleScoringModeChange = (mode: 'full' | 'partial') => {
    setScoringMode(mode)
    localStorage.setItem('scoringMode', mode)
  }

  const { data, isLoading, error } = useRecommendations(selected, scoringMode)

  useEffect(() => {
    getPerspectives().then(setPerspectives)
  }, [])

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>おすすめ銘柄</h2>
      {perspectives.length > 0 && (
        <div className={styles.tabsAndToggle}>
          <PerspectiveTabs
            perspectives={perspectives}
            selected={selected}
            onSelect={handleSelect}
          />
          <div className={styles.scoringModeToggle}>
            <button
              className={`${styles.toggleButton} ${scoringMode === 'full' ? styles.active : ''}`}
              onClick={() => handleScoringModeChange('full')}
            >
              総合評価
            </button>
            <button
              className={`${styles.toggleButton} ${scoringMode === 'partial' ? styles.active : ''}`}
              onClick={() => handleScoringModeChange('partial')}
            >
              軸別評価
            </button>
          </div>
        </div>
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
    </section>
  )
}
