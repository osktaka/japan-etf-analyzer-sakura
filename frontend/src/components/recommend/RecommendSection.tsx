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
}

export function RecommendSection({
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
}: RecommendSectionProps) {
  const [perspectives, setPerspectives] = useState<Perspective[]>([])
  const [selected, setSelected] = useState('popular')
  const { data, isLoading, error } = useRecommendations(selected)

  useEffect(() => {
    getPerspectives().then(setPerspectives)
  }, [])

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>おすすめETF</h2>
      {perspectives.length > 0 && (
        <PerspectiveTabs
          perspectives={perspectives}
          selected={selected}
          onSelect={setSelected}
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
            />
          ))}
        </div>
      )}
    </section>
  )
}
