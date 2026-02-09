/** Holdings tree map component */
import { useMemo, useState, useEffect } from 'react'
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts'
import { Holding } from '../../api/types'
import {
  getStyleFromLabel,
  ALL_MOMENTUM_LABELS,
  MOMENTUM_STYLES,
  MomentumLabel,
} from '../../utils/momentum'
import { formatPrice } from '../../utils'
import { MomentumBadge } from '../common/MomentumBadge'
import styles from './HoldingsTreeMap.module.css'

interface HoldingsTreeMapProps {
  holdings: Holding[]
  onETFClick?: (code: string) => void
}

interface TreemapNode {
  name: string
  size: number
  etf_code: string
  etfName: string
  momentumLabel: string | null
  pnlPercent: number
  annualizedReturn: number | null
  currentValue: number
}

function getContrastColor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#1f2937' : '#ffffff'
}

function getMomentumColor(label: string | null): string {
  return getStyleFromLabel(label)?.color || '#9ca3af'
}

interface CustomContentProps {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  etf_code?: string
  momentumLabel?: string | null
  currentValue?: number
  totalValue: number
  isMobile: boolean
  onETFClick?: (code: string) => void
}

function CustomContent(props: CustomContentProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    name,
    etf_code,
    momentumLabel,
    currentValue = 0,
    totalValue,
    isMobile,
    onETFClick,
  } = props

  const color = getMomentumColor(momentumLabel ?? null)
  const textColor = getContrastColor(color)
  const ratio =
    totalValue > 0
      ? ((currentValue / totalValue) * 100).toFixed(1)
      : '0.0'

  const codeFontSize = isMobile ? 12 : 16
  const ratioFontSize = isMobile ? 10 : 13
  const codeOnlyFontSize = isMobile ? 10 : 14
  const showFull = width >= 60 && height >= 40
  const showCode = width >= 40 && height >= 25

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        stroke="#fff"
        strokeWidth={2}
        rx={4}
        style={{ cursor: onETFClick ? 'pointer' : 'default' }}
        onClick={() => {
          if (onETFClick && etf_code) {
            onETFClick(etf_code)
          }
        }}
      />
      {showFull && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            fill={textColor}
            fontSize={codeFontSize}
            fontWeight={600}
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + (isMobile ? 10 : 14)}
            textAnchor="middle"
            fill={textColor}
            fontSize={ratioFontSize}
          >
            {ratio}%
          </text>
        </>
      )}
      {!showFull && showCode && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 4}
          textAnchor="middle"
          fill={textColor}
          fontSize={codeOnlyFontSize}
          fontWeight={600}
        >
          {name}
        </text>
      )}
    </g>
  )
}

interface CustomTooltipProps {
  active?: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: any[]
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload as TreemapNode | undefined
  if (!data) return null

  const pnlClass =
    data.pnlPercent >= 0 ? styles.tooltipPositive : styles.tooltipNegative

  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipHeader}>
        <span className={styles.tooltipCode}>{data.etf_code}</span>
        {data.momentumLabel && (
          <MomentumBadge label={data.momentumLabel} size="sm" />
        )}
      </div>
      <div className={styles.tooltipName}>{data.etfName}</div>
      <div className={styles.tooltipRow}>
        <span className={styles.tooltipLabel}>評価額</span>
        <span className={styles.tooltipValue}>
          {formatPrice(data.currentValue)}
        </span>
      </div>
      <div className={styles.tooltipRow}>
        <span className={styles.tooltipLabel}>損益率</span>
        <span className={`${styles.tooltipValue} ${pnlClass}`}>
          {data.pnlPercent >= 0 ? '+' : ''}
          {data.pnlPercent.toFixed(2)}%
        </span>
      </div>
      {data.annualizedReturn != null && (
        <div className={styles.tooltipRow}>
          <span className={styles.tooltipLabel}>年率リターン</span>
          <span
            className={`${styles.tooltipValue} ${
              data.annualizedReturn >= 0
                ? styles.tooltipPositive
                : styles.tooltipNegative
            }`}
          >
            {data.annualizedReturn >= 0 ? '+' : ''}
            {data.annualizedReturn.toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  )
}

export function HoldingsTreeMap({
  holdings,
  onETFClick,
}: HoldingsTreeMapProps) {
  const [isMobile, setIsMobile] = useState(() =>
    window.matchMedia('(max-width: 640px)').matches
  )

  useEffect(() => {
    const mql = window.matchMedia('(max-width: 640px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  const totalValue = useMemo(
    () => holdings.reduce((sum, h) => sum + h.current_value, 0),
    [holdings]
  )

  const treeData = useMemo(() => {
    const children: TreemapNode[] = holdings
      .filter((h) => h.current_value > 0)
      .map((h) => ({
        name: h.etf_code,
        size: h.current_value,
        etf_code: h.etf_code,
        etfName: h.etf?.name || '',
        momentumLabel: h.etf?.momentum_label ?? null,
        pnlPercent: h.unrealized_pnl_percent,
        annualizedReturn: h.annualized_return ?? null,
        currentValue: h.current_value,
      }))
    return children
  }, [holdings])

  const momentumRatios = useMemo(() => {
    if (totalValue === 0) return {} as Record<string, number>
    const sums: Record<string, number> = {}
    for (const h of holdings) {
      const label = h.etf?.momentum_label || '不明'
      sums[label] = (sums[label] || 0) + h.current_value
    }
    const ratios: Record<string, number> = {}
    for (const [label, sum] of Object.entries(sums)) {
      ratios[label] = (sum / totalValue) * 100
    }
    return ratios
  }, [holdings, totalValue])

  if (treeData.length === 0) return null

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>勢いヒートマップ</h3>
      </div>
      <div className={styles.chartWrapper}>
        <ResponsiveContainer width="100%" height={isMobile ? 300 : 400}>
          <Treemap
            data={treeData}
            dataKey="size"
            aspectRatio={4 / 3}
            content={
              <CustomContent
                totalValue={totalValue}
                isMobile={isMobile}
                onETFClick={onETFClick}
              />
            }
          >
            <Tooltip content={<CustomTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>
      <div className={styles.legend}>
        {ALL_MOMENTUM_LABELS.map((label: MomentumLabel) => {
          const ratio = momentumRatios[label]
          if (ratio == null) return null
          return (
            <div key={label} className={styles.legendItem}>
              <span
                className={styles.legendDot}
                style={{ backgroundColor: MOMENTUM_STYLES[label].color }}
              />
              <span className={styles.legendLabel}>{label}</span>
              <span
                className={styles.legendRatio}
                style={{ fontSize: `${0.7 + (ratio / 100) * 1.3}rem` }}
              >
                {ratio.toFixed(1)}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default HoldingsTreeMap
