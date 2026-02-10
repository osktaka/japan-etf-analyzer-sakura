/** ETF detail modal component */
import { useEffect, useMemo, useState } from 'react'
import {
  useETFDetail,
  usePortfolio,
  useChartPeriodStorage,
  useTrades,
} from '../../hooks'
import { getPerspectives, Perspective, CustomWeights } from '../../api'
import {
  formatPercent,
  formatAssets,
  formatDate,
  formatVolume,
  formatTradingValue,
  PERSPECTIVE_GRADIENTS,
} from '../../utils'
import { annualizeReturn } from '../../utils/chartUtils'
import { Loading, ErrorMessage, MomentumBadge } from '../common'
import { TagBadge } from '../etf'
import { FavoriteButton } from '../favorite'
import { CompareCheckbox } from '../actions'
import { PerspectiveTabs } from '../recommend'
import {
  MultiPeriodChart,
  ChartPeriodSelector,
  AnnualizedReturnCards,
} from '../chart'
import { MomentumHistoryModal } from './MomentumHistoryModal'
import styles from './ETFDetailModal.module.css'

type PerspectiveKey =
  | 'balance'
  | 'dividend'
  | 'low-cost'
  | 'stability'
  | 'volume'
  | 'growth'
  | 'custom'

const PERSPECTIVE_TO_SCORE_KEY: Record<PerspectiveKey, string> = {
  balance: 'score_balance',
  dividend: 'score_dividend',
  'low-cost': 'score_low_cost',
  stability: 'score_stability',
  volume: 'score_volume',
  growth: 'score_growth',
  custom: 'score_custom',
}

interface ETFDetailModalProps {
  code: string | null
  onClose: () => void
  isInCompare?: boolean
  onCompareToggle?: () => void
  isFavorite?: boolean
  onFavoriteToggle?: () => void
  initialPerspective?: PerspectiveKey
  onCustomClick?: () => void
  customWeights?: CustomWeights | null
}

export function ETFDetailModal({
  code,
  onClose,
  isInCompare,
  onCompareToggle,
  isFavorite,
  onFavoriteToggle,
  initialPerspective,
  onCustomClick,
  customWeights,
}: ETFDetailModalProps) {
  const { data, isLoading, error, refetch } = useETFDetail(code)
  const { holdings } = usePortfolio({ skipSummary: true })
  const { chartPeriods, setChartPeriods } = useChartPeriodStorage()
  const { trades: allTrades } = useTrades(data?.code, { enabled: !!data?.code })
  const trades = useMemo(
    () => allTrades.filter((t) => t.etf_code === data?.code),
    [allTrades, data?.code]
  )
  const [showMomentumHistory, setShowMomentumHistory] = useState(false)
  const [selectedPerspective, setSelectedPerspective] =
    useState<PerspectiveKey>(initialPerspective ?? 'balance')
  const [perspectives, setPerspectives] = useState<Perspective[]>([])

  useEffect(() => {
    getPerspectives().then(setPerspectives)
  }, [])

  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  const handleCustomClick = onCustomClick
    ? () => {
        if (customWeights) {
          setSelectedPerspective('custom')
        } else {
          onCustomClick()
        }
      }
    : undefined

  const annualizedReturns = useMemo(() => {
    const rates = data?.regression_rates
    return chartPeriods.map((period) => {
      const raw = rates?.[period] ?? null
      if (raw === null || raw === undefined) {
        return { period, annualizedReturn: null }
      }
      return {
        period,
        annualizedReturn: annualizeReturn(raw, period),
      }
    })
  }, [data, chartPeriods])

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
    const dataWithScore = data as unknown as Record<
      string,
      number | null | undefined
    >
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
                  <MomentumBadge label={data.momentum_label} code={data.code} />
                </div>
                {onCompareToggle && (
                  <div className={styles.headerCompare}>
                    <CompareCheckbox
                      isInCompare={isInCompare ?? false}
                      onToggle={onCompareToggle}
                      size="lg"
                    />
                  </div>
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

            <div style={{ marginBottom: 'var(--spacing-md)' }}>
              <PerspectiveTabs
                perspectives={perspectives}
                selected={selectedPerspective}
                onSelect={(id) => setSelectedPerspective(id as PerspectiveKey)}
                onCustomClick={handleCustomClick}
              />
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
              <div className={styles.chartHeader}>
                <AnnualizedReturnCards
                  data={annualizedReturns}
                  momentumLabel={data.momentum_label}
                  code={data.code}
                  onHistoryClick={() => setShowMomentumHistory(true)}
                />
                <ChartPeriodSelector
                  selectedPeriods={chartPeriods}
                  onChange={setChartPeriods}
                />
              </div>
              <MultiPeriodChart code={data.code} periods={chartPeriods} trades={trades} />
            </div>

            <div className={styles.footer}>
              <span className={styles.listingDate}>
                上場日: {formatDate(data.listing_date)}
              </span>
            </div>
          </>
        )}

        {showMomentumHistory && data && (
          <MomentumHistoryModal
            code={data.code}
            onClose={() => setShowMomentumHistory(false)}
          />
        )}
      </div>
    </div>
  )
}
