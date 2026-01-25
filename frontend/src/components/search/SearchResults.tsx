/** Search results component */
import { ETFSummary } from '../../api'
import { ETFCard } from '../etf'
import { Loading, ErrorMessage } from '../common'
import styles from './SearchResults.module.css'

interface SearchResultsProps {
  items: ETFSummary[]
  isLoading: boolean
  error: Error | null
  onETFClick: (code: string) => void
  isInCompare?: (code: string) => boolean
  onCompareToggle?: (code: string) => void
  isFavorite?: (code: string) => boolean
  onFavoriteToggle?: (code: string) => void
}

export function SearchResults({
  items,
  isLoading,
  error,
  onETFClick,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
}: SearchResultsProps) {
  if (isLoading) {
    return <Loading message="検索中..." />
  }

  if (error) {
    return <ErrorMessage message="検索に失敗しました" />
  }

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <p>検索結果がありません</p>
      </div>
    )
  }

  return (
    <div className={styles.grid}>
      {items.map((etf) => (
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
  )
}
