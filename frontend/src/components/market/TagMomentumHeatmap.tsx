/** Tag momentum heatmap component using Recharts Treemap */
import { useMemo, useState, useEffect } from 'react'
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts'
import type { TagMomentum } from '../../api/types'
import { getMomentumScoreColor } from '../../utils/momentum'
import styles from './TagMomentumHeatmap.module.css'

interface TagMomentumHeatmapProps {
  data: TagMomentum[]
  onTagClick?: (tagId: number) => void
}

interface TreemapNode {
  name: string
  size: number
  id: number
  color: string
  category: string
  etf_count: number
  momentum_score: number
  momentum_distribution: Record<string, number>
  dominant_label: string | null
}

function getContrastColor(hex: string): string {
  // hsl形式の場合はRGBに変換
  if (hex.startsWith('hsl')) {
    const match = hex.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/)
    if (match) {
      const h = parseInt(match[1]) / 360
      const s = parseInt(match[2]) / 100
      const l = parseInt(match[3]) / 100
      const rgb = hslToRgb(h, s, l)
      const luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
      return luminance > 0.5 ? '#1f2937' : '#ffffff'
    }
  }
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#1f2937' : '#ffffff'
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  let r: number, g: number, b: number
  if (s === 0) {
    r = g = b = l
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1
      if (t > 1) t -= 1
      if (t < 1 / 6) return p + (q - p) * 6 * t
      if (t < 1 / 2) return q
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6
      return p
    }
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s
    const p = 2 * l - q
    r = hue2rgb(p, q, h + 1 / 3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1 / 3)
  }
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]
}

interface CustomContentProps {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  id?: number
  etf_count?: number
  momentum_score?: number
  isMobile: boolean
  onTagClick?: (tagId: number) => void
}

function CustomContent(props: CustomContentProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    name,
    id,
    etf_count,
    momentum_score = 50,
    isMobile,
    onTagClick,
  } = props

  const color = getMomentumScoreColor(momentum_score)
  const textColor = getContrastColor(color)

  const nameFontSize = isMobile ? 11 : 14
  const countFontSize = isMobile ? 9 : 11
  const nameOnlyFontSize = isMobile ? 9 : 12
  const showFull = width >= 60 && height >= 40
  const showName = width >= 40 && height >= 25

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
        style={{ cursor: onTagClick ? 'pointer' : 'default' }}
        onClick={() => {
          if (onTagClick && id != null) {
            onTagClick(id)
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
            fontSize={nameFontSize}
            fontWeight={600}
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + (isMobile ? 8 : 12)}
            textAnchor="middle"
            fill={textColor}
            fontSize={countFontSize}
          >
            {etf_count}銘柄
          </text>
        </>
      )}
      {!showFull && showName && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 4}
          textAnchor="middle"
          fill={textColor}
          fontSize={nameOnlyFontSize}
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

  const distributionEntries = Object.entries(data.momentum_distribution).filter(
    ([, count]) => count > 0
  )

  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipHeader}>{data.name}</div>
      <div className={styles.tooltipScore}>
        勢いスコア: {data.momentum_score.toFixed(0)}
      </div>
      <div className={styles.tooltipRow}>
        <span className={styles.tooltipLabel}>ETF数</span>
        <span className={styles.tooltipValue}>{data.etf_count}銘柄</span>
      </div>
      {distributionEntries.length > 0 && (
        <div className={styles.tooltipDistribution}>
          <div className={styles.tooltipDistTitle}>内訳</div>
          {distributionEntries.map(([label, count]) => (
            <div key={label} className={styles.tooltipDistItem}>
              <span className={styles.tooltipDistLabel}>{label}</span>
              <span className={styles.tooltipDistCount}>{count}件</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function TagMomentumHeatmap({
  data,
  onTagClick,
}: TagMomentumHeatmapProps) {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia('(max-width: 640px)').matches
  )

  useEffect(() => {
    const mql = window.matchMedia('(max-width: 640px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  const treeData = useMemo(
    () =>
      data
        .filter((tag) => tag.etf_count > 0)
        .map((tag) => ({
          ...tag,
          name: tag.name,
          size: tag.etf_count,
        })),
    [data]
  )

  if (treeData.length === 0) return null

  return (
    <div className={styles.container}>
      <div className={styles.chartWrapper}>
        <ResponsiveContainer width="100%" height={isMobile ? 250 : 350}>
          <Treemap
            data={treeData}
            dataKey="size"
            aspectRatio={4 / 3}
            content={
              <CustomContent isMobile={isMobile} onTagClick={onTagClick} />
            }
          >
            <Tooltip content={<CustomTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default TagMomentumHeatmap
