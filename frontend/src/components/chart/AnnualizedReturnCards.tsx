/** Annualized return cards component */
import { useState, useRef, useEffect } from 'react'
import { ChartPeriod } from '../../api'
import { CHART_PERIODS } from '../../utils/constants'
import { formatReturn } from '../../utils/chartUtils'
import { getMomentumInfoFromAnnualized } from '../../utils/momentum'
import { MomentumBadge } from '../common'
import styles from './AnnualizedReturnCards.module.css'

const TOOLTIP_TEXT =
  '回帰直線の上昇率を期間ごとに算出し、さらに1年換算した値です。株価上昇の勢いを見ることができます'

interface AnnualizedReturnData {
  period: ChartPeriod
  annualizedReturn: number | null
}

interface AnnualizedReturnCardsProps {
  data: AnnualizedReturnData[]
  momentumLabel?: string | null
  code?: string
  onHistoryClick?: () => void
}

const PERIOD_ORDER: ChartPeriod[] = [
  '1m',
  '3m',
  '6m',
  '1y',
  '3y',
  '5y',
  '10y',
  '20y',
]

export function AnnualizedReturnCards({
  data,
  momentumLabel,
  code,
  onHistoryClick,
}: AnnualizedReturnCardsProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const helpIconRef = useRef<HTMLSpanElement | null>(null)

  const sortedData = [...data].sort(
    (a, b) => PERIOD_ORDER.indexOf(a.period) - PERIOD_ORDER.indexOf(b.period)
  )

  // Use momentum_label from backend if available, fallback to local calculation
  const resolvedMomentumLabel = (() => {
    if (momentumLabel) return momentumLabel
    const annual1m =
      data.find((d) => d.period === '1m')?.annualizedReturn ?? null
    const annual3m =
      data.find((d) => d.period === '3m')?.annualizedReturn ?? null
    return getMomentumInfoFromAnnualized(annual1m, annual3m)?.label ?? null
  })()

  const getPeriodLabel = (period: ChartPeriod): string => {
    const found = CHART_PERIODS.find((p) => p.id === period)
    return found?.label ?? period
  }

  const handleHelpClick = () => {
    setShowTooltip((prev) => !prev)
  }

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!showTooltip) return
      const target = event.target as Node
      const isInsideTooltip = tooltipRef.current?.contains(target)
      const isInsideHelpIcon = helpIconRef.current?.contains(target)
      if (!isInsideTooltip && !isInsideHelpIcon) {
        setShowTooltip(false)
      }
    }
    // キャプチャフェーズで捕捉（モーダルのstopPropagation対策）
    document.addEventListener('click', handleClickOutside, true)
    return () => document.removeEventListener('click', handleClickOutside, true)
  }, [showTooltip])

  return (
    <div className={styles.wrapper}>
      <div className={styles.titleRow}>
        <span className={styles.title}>年率回帰上昇率</span>
        <span
          ref={helpIconRef}
          className={styles.helpIcon}
          onClick={handleHelpClick}
          aria-label="年率回帰上昇率の説明を表示"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              handleHelpClick()
            }
          }}
        >
          ?
        </span>
        {onHistoryClick && (
          <button
            className={styles.historyLink}
            onClick={onHistoryClick}
            type="button"
          >
            履歴
          </button>
        )}
        {showTooltip && (
          <div ref={tooltipRef} className={styles.tooltip}>
            {TOOLTIP_TEXT}
          </div>
        )}
      </div>
      <div className={styles.container}>
        {sortedData.map(({ period, annualizedReturn }) => (
          <div key={period} className={styles.card}>
            <span className={styles.period}>{getPeriodLabel(period)}</span>
            <span
              className={`${styles.value} ${
                annualizedReturn === null
                  ? ''
                  : annualizedReturn >= 0
                    ? styles.positive
                    : styles.negative
              }`}
            >
              {formatReturn(annualizedReturn)}
            </span>
          </div>
        ))}
        {resolvedMomentumLabel && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              alignSelf: 'center',
              marginLeft: 'var(--spacing-sm)',
            }}
          >
            <MomentumBadge
              label={resolvedMomentumLabel}
              size="md"
              code={code}
            />
          </span>
        )}
      </div>
    </div>
  )
}
