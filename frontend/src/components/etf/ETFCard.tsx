/** ETF card component */
import { ETFSummary } from '../../api'
import { formatPrice, formatPercent } from '../../utils'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import { TagBadge } from './TagBadge'
import styles from './ETFCard.module.css'

interface ETFCardProps {
  etf: ETFSummary
  onClick?: () => void
  isSelected?: boolean
  showCompareButton?: boolean
  onCompareToggle?: () => void
  isFavorite?: boolean
  onFavoriteToggle?: () => void
}

export function ETFCard({
  etf,
  onClick,
  isSelected,
  showCompareButton,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
}: ETFCardProps) {
  return (
    <div
      className={`${styles.card} ${isSelected ? styles.selected : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      <div className={styles.header}>
        {onFavoriteToggle && (
          <FavoriteButton
            isFavorite={isFavorite ?? false}
            onClick={onFavoriteToggle}
            size="sm"
          />
        )}
        <span className={styles.code}>{etf.code}</span>
        {etf.category && (
          <span className={styles.category}>{etf.category}</span>
        )}
        {showCompareButton && onCompareToggle && (
          <CompareCheckbox
            isInCompare={isSelected ?? false}
            onToggle={onCompareToggle}
            size="sm"
          />
        )}
      </div>
      <h3 className={styles.name}>{etf.name}</h3>
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <span className={styles.label}>価格</span>
          <span className={styles.value}>{formatPrice(etf.market_price)}</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>配当利回り</span>
          <span className={styles.value}>
            {formatPercent(etf.dividend_yield)}
          </span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>信託報酬</span>
          <span className={styles.value}>
            {formatPercent(etf.expense_ratio)}
          </span>
        </div>
      </div>
      {etf.tags.length > 0 && (
        <div className={styles.tags}>
          {etf.tags.slice(0, 3).map((tag) => (
            <TagBadge key={tag.id} tag={tag} size="sm" />
          ))}
        </div>
      )}
    </div>
  )
}
