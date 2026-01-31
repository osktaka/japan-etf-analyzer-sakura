/** ETF detail modal component */
import { useMemo, useState } from 'react'
import { useETFDetail, usePortfolio } from '../../hooks'
import {
  formatPercent,
  formatAssets,
  formatDate,
  formatVolume,
  formatTradingValue,
  PERSPECTIVE_COLORS,
  PERSPECTIVE_GRADIENTS,
} from '../../utils'
import { Loading, ErrorMessage } from '../common'
import { TagBadge } from '../etf'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import { MultiPeriodChart } from '../chart'
import styles from './ETFDetailModal.module.css'

type PerspectiveKey =
  | 'balance'
  | 'dividend'
  | 'low-cost'
  | 'stability'
  | 'volume'
  | 'growth'

const PERSPECTIVES: { key: PerspectiveKey; label: string }[] = [
  { key: 'balance', label: 'バランス' },
  { key: 'dividend', label: '配当収入' },
  { key: 'low-cost', label: '低コスト' },
  { key: 'stability', label: '安定性' },
  { key: 'volume', label: '取引規模' },
  { key: 'growth', label: '成長性' },
]

const PERSPECTIVE_TO_SCORE_KEY: Record<PerspectiveKey, string> = {
  balance: 'score_balance',
  dividend: 'score_dividend',
  'low-cost': 'score_low_cost',
  stability: 'score_stability',
  volume: 'score_volume',
  growth: 'score_growth',
}

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
  const [selectedPerspective, setSelectedPerspective] =
    useState<PerspectiveKey>('balance')

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  // 選択中の切り口のスコアを取得（フォールバックとしてdata.scoreを使用）
  const currentScore = useMemo(() => {
    if (!data) return null
    const scoreKey = PERSPECTIVE_TO_SCORE_KEY[selectedPerspective]
    const scoreValue = (
      data as unknown as Record<string, number | null | undefined>
    )[scoreKey]
    // 切り口ごとのスコアがない場合は、デフォルトスコアを使用
    if (scoreValue !== undefined && scoreValue !== null) {
      return scoreValue
    }
    // フォールバック: data.scoreを使用
    const dataWithScore = data as unknown as Record<string, number | null | undefined>
    return dataWithScore.score !== undefined && dataWithScore.score !== null
      ? dataWithScore.score
      : null
  }, [data, selectedPerspective])

  // 選択中の切り口のグラデーションを取得
  const perspectiveGradient =
    PERSPECTIVE_GRADIENTS[selectedPerspective] || PERSPECTIVE_GRADIENTS.balance

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

            {data.description && (
              <p className={styles.description}>{data.description}</p>
            )}

            <div className={styles.perspectiveTabs}>
              {PERSPECTIVES.map(({ key, label }) => {
                const isActive = selectedPerspective === key
                const activeColor = PERSPECTIVE_COLORS[key] || PERSPECTIVE_COLORS.balance
                return (
                  <button
                    key={key}
                    className={`${styles.perspectiveTab} ${isActive ? styles.active : ''}`}
                    onClick={() => setSelectedPerspective(key)}
                    type="button"
                    style={
                      isActive
                        ? {
                            backgroundColor: activeColor,
                            borderColor: activeColor,
                            color: 'white',
                          }
                        : undefined
                    }
                  >
                    {label}
                  </button>
                )
              })}
            </div>

            {currentScore !== null && (
              <div
                className={styles.scoreSection}
                style={{ background: perspectiveGradient }}
              >
                <span className={styles.scoreLabel}>評価スコア</span>
                <span className={styles.scoreValue}>
                  {Math.round(currentScore)}点
                </span>
              </div>
            )}

            {data.axis_scores && (
              <div className={styles.axisScores}>
                <div className={styles.axisScore}>
                  <span className={styles.axisLabel}>配当力</span>
                  <span className={styles.axisValue}>
                    {data.axis_scores.dividend_power !== null
                      ? Math.round(data.axis_scores.dividend_power)
                      : '-'}
                  </span>
                </div>
                <div className={styles.axisScore}>
                  <span className={styles.axisLabel}>コスト</span>
                  <span className={styles.axisValue}>
                    {data.axis_scores.cost_efficiency !== null
                      ? Math.round(data.axis_scores.cost_efficiency)
                      : '-'}
                  </span>
                </div>
                <div className={styles.axisScore}>
                  <span className={styles.axisLabel}>安定</span>
                  <span className={styles.axisValue}>
                    {data.axis_scores.scale_reliability !== null
                      ? Math.round(data.axis_scores.scale_reliability)
                      : '-'}
                  </span>
                </div>
                <div className={styles.axisScore}>
                  <span className={styles.axisLabel}>規模</span>
                  <span className={styles.axisValue}>
                    {data.axis_scores.trading_quality !== null
                      ? Math.round(data.axis_scores.trading_quality)
                      : '-'}
                  </span>
                </div>
                <div className={styles.axisScore}>
                  <span className={styles.axisLabel}>リターン</span>
                  <span className={styles.axisValue}>
                    {data.axis_scores.return_performance !== null
                      ? Math.round(data.axis_scores.return_performance)
                      : '-'}
                  </span>
                </div>
              </div>
            )}

            <div className={styles.metrics}>
              <div className={styles.metricGroup}>
                <h4 className={styles.groupTitle}>配当力</h4>
                <div className={styles.metric}>
                  <span className={styles.label}>配当利回り</span>
                  <span className={styles.value}>
                    {formatPercent(data.dividend_yield)}
                  </span>
                </div>
              </div>

              <div className={styles.metricGroup}>
                <h4 className={styles.groupTitle}>コスト効率</h4>
                <div className={styles.metric}>
                  <span className={styles.label}>信託報酬</span>
                  <span className={styles.value}>
                    {formatPercent(data.expense_ratio)}
                  </span>
                </div>
              </div>

              <div className={styles.metricGroup}>
                <h4 className={styles.groupTitle}>安定性</h4>
                <div className={styles.metric}>
                  <span className={styles.label}>純資産総額</span>
                  <span className={styles.value}>
                    {formatAssets(data.total_assets)}
                  </span>
                </div>
              </div>

              <div className={styles.metricGroup}>
                <h4 className={styles.groupTitle}>取引規模</h4>
                <div className={styles.metric}>
                  <span className={styles.label}>売買代金</span>
                  <span className={styles.value}>
                    {formatTradingValue(data.trading_value)}
                  </span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.label}>30日出来高平均</span>
                  <span className={styles.value}>
                    {formatVolume(data.average_volume)}
                  </span>
                </div>
              </div>

              <div className={styles.metricGroup}>
                <h4 className={styles.groupTitle}>リターン実績</h4>
                <div className={styles.metric}>
                  <span className={styles.label}>1年リターン</span>
                  <span className={styles.value}>
                    {formatPercent(data.return_1y)}
                  </span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.label}>3年リターン</span>
                  <span className={styles.value}>
                    {formatPercent(data.return_3y)}
                  </span>
                </div>
              </div>
            </div>

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
