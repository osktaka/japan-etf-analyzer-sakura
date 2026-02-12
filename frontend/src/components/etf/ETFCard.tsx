/** ETF card component */
import { ETFSummary, AxisScores } from '../../api'
import { formatPrice, formatPercent, PERSPECTIVE_GRADIENTS } from '../../utils'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import { MomentumBadge } from '../common'
import { TagBadge } from './TagBadge'
import styles from './ETFCard.module.css'

interface ETFCardProps {
  etf: ETFSummary & { score?: number | null; axis_scores?: AxisScores }
  onClick?: () => void
  isSelected?: boolean
  showCompareButton?: boolean
  onCompareToggle?: () => void
  isFavorite?: boolean
  onFavoriteToggle?: () => void
  isHolding?: boolean
  perspective?: string
  readOnly?: boolean
}

export function ETFCard({
  etf,
  onClick,
  isSelected,
  showCompareButton,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
  isHolding,
  perspective,
  readOnly,
}: ETFCardProps) {
  const scoreGradient = perspective
    ? PERSPECTIVE_GRADIENTS[perspective] || PERSPECTIVE_GRADIENTS.balance
    : PERSPECTIVE_GRADIENTS.balance

  return (
    <div
      className={`${styles.card} ${isSelected ? styles.selected : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      <div className={styles.header}>
        {(readOnly || onFavoriteToggle) && (
          <FavoriteButton
            isFavorite={isFavorite ?? false}
            onClick={() => onFavoriteToggle?.()}
            size="sm"
            isHolding={isHolding}
            disabled={readOnly}
          />
        )}
        <span className={styles.code}>{etf.code}</span>
        {etf.category && (
          <span className={styles.category}>{etf.category}</span>
        )}
        <MomentumBadge label={etf.momentum_label} code={etf.code} />
        {showCompareButton && onCompareToggle && (
          <CompareCheckbox
            isInCompare={isSelected ?? false}
            onToggle={onCompareToggle}
            size="sm"
          />
        )}
      </div>
      <h3 className={styles.name} title={etf.name}>
        {etf.name}
      </h3>
      {etf.score !== undefined && etf.score !== null && (
        <div
          className={styles.scoreSection}
          style={{ background: scoreGradient }}
        >
          <span className={styles.scoreLabel}>評価スコア</span>
          <span className={styles.scoreValue}>{Math.round(etf.score)}点</span>
        </div>
      )}
      {etf.axis_scores && (
        <div className={styles.axisScores}>
          <div className={styles.axisScore}>
            <span className={styles.axisLabel}>配当力</span>
            <span className={styles.axisValue}>
              {etf.axis_scores.dividend_power !== null
                ? Math.round(etf.axis_scores.dividend_power)
                : '-'}
            </span>
          </div>
          <div className={styles.axisScore}>
            <span className={styles.axisLabel}>コスト</span>
            <span className={styles.axisValue}>
              {etf.axis_scores.cost_efficiency !== null
                ? Math.round(etf.axis_scores.cost_efficiency)
                : '-'}
            </span>
          </div>
          <div className={styles.axisScore}>
            <span className={styles.axisLabel}>安定</span>
            <span className={styles.axisValue}>
              {etf.axis_scores.scale_reliability !== null
                ? Math.round(etf.axis_scores.scale_reliability)
                : '-'}
            </span>
          </div>
          <div className={styles.axisScore}>
            <span className={styles.axisLabel}>規模</span>
            <span className={styles.axisValue}>
              {etf.axis_scores.trading_quality !== null
                ? Math.round(etf.axis_scores.trading_quality)
                : '-'}
            </span>
          </div>
          <div className={styles.axisScore}>
            <span className={styles.axisLabel}>リターン</span>
            <span className={styles.axisValue}>
              {etf.axis_scores.return_performance !== null
                ? Math.round(etf.axis_scores.return_performance)
                : '-'}
            </span>
          </div>
        </div>
      )}
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
          {etf.tags.map((tag) => (
            <TagBadge key={tag.id} tag={tag} size="sm" />
          ))}
        </div>
      )}
    </div>
  )
}
