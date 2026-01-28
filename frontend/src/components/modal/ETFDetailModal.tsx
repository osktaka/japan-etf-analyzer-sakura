/** ETF detail modal component */
import { useMemo } from 'react'
import { useETFDetail, usePortfolio } from '../../hooks'
import {
  formatPrice,
  formatPercent,
  formatAssets,
  formatDate,
} from '../../utils'
import { Loading, ErrorMessage } from '../common'
import { TagBadge } from '../etf'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import { MultiPeriodChart } from '../chart'
import styles from './ETFDetailModal.module.css'

interface ETFDetailModalProps {
  code: string | null
  onClose: () => void
  isInCompare?: boolean
  onCompareToggle?: () => void
  isFavorite?: boolean
  onFavoriteToggle?: () => void
}

export function ETFDetailModal({
  code,
  onClose,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
}: ETFDetailModalProps) {
  const { data, isLoading, error, refetch } = useETFDetail(code)
  const { holdings } = usePortfolio()

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  if (!code) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>

        {isLoading && <Loading />}
        {error && (
          <ErrorMessage
            message="データの取得に失敗しました"
            onRetry={refetch}
          />
        )}

        {data && (
          <>
            <div className={styles.header}>
              <div className={styles.headerTop}>
                <div className={styles.headerLeft}>
                  {onFavoriteToggle && (
                    <FavoriteButton
                      isFavorite={isFavorite ?? false}
                      onClick={onFavoriteToggle}
                      size="lg"
                      isHolding={code ? holdingCodes.has(code) : false}
                    />
                  )}
                  <span className={styles.code}>{data.code}</span>
                  {data.category && (
                    <span className={styles.category}>
                      {data.category.name}
                    </span>
                  )}
                </div>
                {onCompareToggle && (
                  <CompareCheckbox
                    isInCompare={isInCompare ?? false}
                    onToggle={onCompareToggle}
                    size="lg"
                  />
                )}
              </div>
              <h2 className={styles.name}>{data.name}</h2>
              {data.tags.length > 0 && (
                <div className={styles.tags}>
                  {data.tags.map((tag) => (
                    <TagBadge key={tag.id} tag={tag} />
                  ))}
                </div>
              )}
            </div>

            <div className={styles.metrics}>
              <div className={styles.metric}>
                <span className={styles.label}>市場価格</span>
                <span className={styles.value}>
                  {formatPrice(data.market_price)}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.label}>基準価額</span>
                <span className={styles.value}>{formatPrice(data.nav)}</span>
              </div>
              <div className={styles.metric}>
                <span className={styles.label}>配当利回り</span>
                <span className={styles.value}>
                  {formatPercent(data.dividend_yield)}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.label}>信託報酬</span>
                <span className={styles.value}>
                  {formatPercent(data.expense_ratio)}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.label}>乖離率</span>
                <span className={styles.value}>
                  {formatPercent(data.deviation_rate)}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.label}>純資産総額</span>
                <span className={styles.value}>
                  {formatAssets(data.total_assets)}
                </span>
              </div>
            </div>

            {data.description && (
              <p className={styles.description}>{data.description}</p>
            )}

            <div className={styles.chart}>
              <MultiPeriodChart code={data.code} />
            </div>

            <div className={styles.footer}>
              <span className={styles.listingDate}>
                上場日: {formatDate(data.listing_date)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
