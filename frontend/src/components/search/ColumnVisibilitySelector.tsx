/** Column visibility selector for table view */
import { PerformancePeriod } from '../../api/types'
import { PERIOD_ORDER } from './PeriodSelector'
import styles from './ETFTableView.module.css'

export interface CommonColumnVisibility {
  price: boolean
  dividendYield: boolean
  expenseRatio: boolean
}

export interface ScoreColumnVisibility {
  dividendPower: boolean
  costEfficiency: boolean
  scaleReliability: boolean
  tradingQuality: boolean
  returnPerformance: boolean
}

interface CommonColumnDef {
  key: keyof CommonColumnVisibility
  label: string
}

const COMMON_COLUMNS: CommonColumnDef[] = [
  { key: 'price', label: '株価' },
  { key: 'dividendYield', label: '分配金利回り' },
  { key: 'expenseRatio', label: '信託報酬' },
]

interface ScoreColumnDef {
  key: keyof ScoreColumnVisibility
  label: string
}

const SCORE_COLUMNS: ScoreColumnDef[] = [
  { key: 'dividendPower', label: '配当力' },
  { key: 'costEfficiency', label: 'コスト' },
  { key: 'scaleReliability', label: '安定性' },
  { key: 'tradingQuality', label: '取引規模' },
  { key: 'returnPerformance', label: 'リターン' },
]

const ALL_PERIODS: { id: PerformancePeriod; label: string }[] = [
  { id: '1m', label: '1M' },
  { id: '3m', label: '3M' },
  { id: '6m', label: '6M' },
  { id: '1y', label: '1Y' },
  { id: '3y', label: '3Y' },
  { id: '5y', label: '5Y' },
  { id: '10y', label: '10Y' },
  { id: '20y', label: '20Y' },
]

interface ColumnVisibilitySelectorProps {
  displayMode: 'score' | 'trend'
  commonColumnVisibility: CommonColumnVisibility
  onCommonColumnVisibilityChange: (v: CommonColumnVisibility) => void
  scoreColumnVisibility: ScoreColumnVisibility
  onScoreColumnVisibilityChange: (v: ScoreColumnVisibility) => void
  selectedPeriods: PerformancePeriod[]
  onPeriodsChange: (periods: PerformancePeriod[]) => void
  momentumVisible: boolean
  onMomentumVisibleChange: (v: boolean) => void
}

export function ColumnVisibilitySelector({
  displayMode,
  commonColumnVisibility,
  onCommonColumnVisibilityChange,
  scoreColumnVisibility,
  onScoreColumnVisibilityChange,
  selectedPeriods,
  onPeriodsChange,
  momentumVisible,
  onMomentumVisibleChange,
}: ColumnVisibilitySelectorProps) {
  const toggleCommon = (key: keyof CommonColumnVisibility) => {
    onCommonColumnVisibilityChange({
      ...commonColumnVisibility,
      [key]: !commonColumnVisibility[key],
    })
  }

  const toggleScore = (key: keyof ScoreColumnVisibility) => {
    onScoreColumnVisibilityChange({
      ...scoreColumnVisibility,
      [key]: !scoreColumnVisibility[key],
    })
  }

  const togglePeriod = (period: PerformancePeriod) => {
    if (selectedPeriods.includes(period)) {
      if (selectedPeriods.length > 1) {
        const newPeriods = selectedPeriods
          .filter((p) => p !== period)
          .sort((a, b) => PERIOD_ORDER.indexOf(a) - PERIOD_ORDER.indexOf(b))
        onPeriodsChange(newPeriods)
      }
    } else {
      const newPeriods = [...selectedPeriods, period].sort(
        (a, b) => PERIOD_ORDER.indexOf(a) - PERIOD_ORDER.indexOf(b)
      )
      onPeriodsChange(newPeriods)
    }
  }

  return (
    <div className={styles.periodSelector}>
      <span className={styles.periodLabel}>列表示:</span>
      <div className={styles.periodButtons}>
        {COMMON_COLUMNS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`${styles.periodButton} ${
              commonColumnVisibility[key] ? styles.periodButtonActive : ''
            }`}
            onClick={() => toggleCommon(key)}
          >
            {label}
          </button>
        ))}
        <button
          type="button"
          className={`${styles.periodButton} ${
            momentumVisible ? styles.periodButtonActive : ''
          }`}
          style={{ marginRight: 'var(--spacing-sm)' }}
          onClick={() => onMomentumVisibleChange(!momentumVisible)}
        >
          勢い
        </button>
        {displayMode === 'score' && (
          <>
            <button
              type="button"
              className={`${styles.periodButton} ${styles.periodButtonActive}`}
              style={{ opacity: 0.7, cursor: 'default' }}
            >
              評価スコア
            </button>
            {SCORE_COLUMNS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className={`${styles.periodButton} ${
                  scoreColumnVisibility[key] ? styles.periodButtonActive : ''
                }`}
                onClick={() => toggleScore(key)}
              >
                {label}
              </button>
            ))}
          </>
        )}
        {displayMode === 'trend' && (
          <>
            {ALL_PERIODS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className={`${styles.periodButton} ${
                  selectedPeriods.includes(id) ? styles.periodButtonActive : ''
                }`}
                onClick={() => togglePeriod(id)}
              >
                {label}
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
