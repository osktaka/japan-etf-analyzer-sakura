/** Holding card component */
import { Holding } from '../../api/types'
import { formatPrice } from '../../utils'
import { MomentumBadge } from '../common'
import { CompareCheckbox } from '../actions/CompareCheckbox'
import styles from './HoldingCard.module.css'

interface HoldingCardProps {
  holding: Holding
  onClick?: () => void
  onHistoryClick?: () => void
  onAddTrade?: () => void
  isInCompare?: boolean
  onCompareToggle?: () => void
  readOnly?: boolean
}

export function HoldingCard({
  holding,
  onClick,
  onHistoryClick,
  onAddTrade,
  isInCompare,
  onCompareToggle,
  readOnly,
}: HoldingCardProps) {
  const pnlClass =
    holding.unrealized_pnl >= 0 ? styles.positive : styles.negative
  const pnlSign = holding.unrealized_pnl >= 0 ? '+' : ''

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick?.()
    }
  }

  return (
    <div
      className={styles.card}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className={styles.header}>
        <span
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <span className={styles.code}>{holding.etf_code}</span>
          <MomentumBadge label={holding.etf?.momentum_label} code={holding.etf_code} />
        </span>
        {onCompareToggle && (
          <div
            className={styles.compareAction}
            onClick={(e) => e.stopPropagation()}
          >
            <CompareCheckbox
              isInCompare={isInCompare ?? false}
              onToggle={onCompareToggle}
              size="sm"
            />
          </div>
        )}
      </div>
      <h3 className={styles.name} title={holding.etf?.name || ''}>
        {holding.etf?.name || '-'}
      </h3>
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <span className={styles.label}>数量</span>
          <span className={styles.value}>{holding.quantity}口</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>評価額</span>
          <span className={styles.value}>
            {formatPrice(holding.current_value)}
          </span>
        </div>
      </div>
      <div className={styles.pnlSection}>
        <div className={styles.pnlItem}>
          <span className={styles.label}>評価損益</span>
          <span className={`${styles.pnlValue} ${pnlClass}`}>
            {pnlSign}
            {formatPrice(holding.unrealized_pnl)}
          </span>
        </div>
        <div className={styles.pnlItem}>
          <span className={styles.label}>損益率</span>
          <span className={`${styles.pnlPercent} ${pnlClass}`}>
            {pnlSign}
            {holding.unrealized_pnl_percent.toFixed(2)}%
          </span>
        </div>
      </div>
      <div className={styles.annualizedSection}>
        <div className={styles.pnlItem}>
          <span className={styles.label}>保有期間</span>
          <span className={styles.value}>{holding.holding_period || '-'}</span>
        </div>
        <div className={styles.pnlItem}>
          <span className={styles.label}>年率リターン</span>
          <span
            className={`${styles.pnlPercent} ${
              holding.annualized_return !== null &&
              holding.annualized_return !== undefined
                ? holding.annualized_return >= 0
                  ? styles.positive
                  : styles.negative
                : ''
            }`}
          >
            {holding.annualized_return !== null &&
            holding.annualized_return !== undefined
              ? `${holding.annualized_return >= 0 ? '+' : ''}${holding.annualized_return.toFixed(2)}%`
              : '-'}
          </span>
        </div>
      </div>
      {(readOnly || onHistoryClick || onAddTrade) && (
        <div className={styles.actions}>
          {(readOnly || onHistoryClick) && (
            <button
              className={styles.historyBtn}
              onClick={(e) => {
                e.stopPropagation()
                onHistoryClick?.()
              }}
              type="button"
              title="取引履歴"
              disabled={readOnly}
            >
              履歴
            </button>
          )}
          {(readOnly || onAddTrade) && (
            <button
              className={styles.tradeBtn}
              onClick={(e) => {
                e.stopPropagation()
                onAddTrade?.()
              }}
              type="button"
              title="取引登録"
              disabled={readOnly}
            >
              取引
            </button>
          )}
        </div>
      )}
    </div>
  )
}
