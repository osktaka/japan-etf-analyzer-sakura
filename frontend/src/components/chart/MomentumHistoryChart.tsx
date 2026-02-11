/** Momentum history line chart with background label segments */
import { useMemo, useState, useEffect } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  ReferenceLine,
  ReferenceArea,
  Line,
  Legend,
  Tooltip,
  TooltipProps,
} from 'recharts'
import { MomentumHistoryItem, ChartDataPoint } from '../../api/types'
import { MOMENTUM_STYLES, MomentumLabel } from '../../utils/momentum'
import { MomentumBadge } from '../common'

interface MomentumHistoryChartProps {
  data: MomentumHistoryItem[]
  rateMode: 'regression' | 'return'
  priceData: ChartDataPoint[]
}

interface ChartRow {
  date: string
  rate1m: number | null
  rate3m: number | null
  momentumLabel: string
  price: number | null
}

interface LabelSegment {
  startDate: string
  endDate: string
  label: string
}

/** Build label segments from consecutive momentum labels */
function buildSegments(rows: ChartRow[]): LabelSegment[] {
  if (rows.length === 0) return []
  const segments: LabelSegment[] = []
  let current: LabelSegment = {
    startDate: rows[0].date,
    endDate: rows[0].date,
    label: rows[0].momentumLabel,
  }
  for (let i = 1; i < rows.length; i++) {
    if (rows[i].momentumLabel === current.label) {
      current.endDate = rows[i].date
    } else {
      segments.push(current)
      current = {
        startDate: rows[i].date,
        endDate: rows[i].date,
        label: rows[i].momentumLabel,
      }
    }
  }
  segments.push(current)
  return segments
}

/** Format rate value with sign and percent */
function formatRate(v: number | null): string {
  if (v === null) return '-'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
}

/** Custom tooltip renderer */
function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null
  const row = payload[0].payload as ChartRow
  const displayDate = row.date.replace(/-/g, '/')

  return (
    <div
      style={{
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: 6,
        padding: '8px 12px',
        fontSize: 13,
      }}
    >
      <div style={{ marginBottom: 4, fontWeight: 600 }}>{displayDate}</div>
      <div style={{ marginBottom: 4 }}>
        <MomentumBadge label={row.momentumLabel} size="sm" />
      </div>
      <div style={{ color: rateColor(row.rate1m) }}>
        1M年率: {formatRate(row.rate1m)}
      </div>
      <div style={{ color: rateColor(row.rate3m) }}>
        3M年率: {formatRate(row.rate3m)}
      </div>
      {row.price !== null && (
        <div style={{ color: '#6b7280' }}>
          株価: {row.price.toLocaleString()}円
        </div>
      )}
    </div>
  )
}

function rateColor(v: number | null): string {
  if (v === null) return '#6b7280'
  return v >= 0 ? '#059669' : '#dc2626'
}

export function MomentumHistoryChart({
  data,
  rateMode,
  priceData,
}: MomentumHistoryChartProps) {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia('(max-width: 640px)').matches
  )
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 640px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  const { chartData, segments } = useMemo(() => {
    const reversed = data.slice().reverse()
    const prefix = rateMode === 'regression' ? 'regression_rate' : 'return_rate'
    const priceMap = new Map(priceData.map((p) => [p.date, p.close]))

    const rows: ChartRow[] = reversed.map((item) => {
      const raw1m = item[`${prefix}_1m` as keyof MomentumHistoryItem] as
        | number
        | null
      const raw3m = item[`${prefix}_3m` as keyof MomentumHistoryItem] as
        | number
        | null
      return {
        date: item.date,
        rate1m:
          raw1m !== null ? Math.round(raw1m * 12 * 1000) / 1000 : null,
        rate3m:
          raw3m !== null ? Math.round(raw3m * 4 * 1000) / 1000 : null,
        momentumLabel: item.momentum_label,
        price: priceMap.get(item.date) ?? null,
      }
    })

    return { chartData: rows, segments: buildSegments(rows) }
  }, [data, rateMode, priceData])

  const tickFormatter = (value: string) => {
    const parts = value.split('-')
    return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : value
  }

  const yTickFormatter = (value: number) => `${value.toFixed(1)}%`

  if (chartData.length === 0) return null

  return (
    <ResponsiveContainer width="100%" height={isMobile ? 200 : 280}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={tickFormatter} fontSize={11} />
        <YAxis yAxisId="left" tickFormatter={yTickFormatter} fontSize={11} width={52} />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickFormatter={(v: number) => v.toLocaleString()}
          fontSize={11}
          width={52}
        />
        <ReferenceLine yAxisId="left" y={0} stroke="#9ca3af" strokeDasharray="3 3" />
        {segments.map((seg, i) => {
          const style =
            MOMENTUM_STYLES[seg.label as MomentumLabel] ?? null
          if (!style) return null
          return (
            <ReferenceArea
              key={i}
              yAxisId="left"
              x1={seg.startDate}
              x2={seg.endDate}
              fill={style.bgColor}
              fillOpacity={1}
            />
          )
        })}
        <Line
          yAxisId="left"
          dataKey="rate1m"
          stroke="#3B82F6"
          strokeWidth={2}
          dot={false}
          connectNulls={true}
          name="1M年率"
        />
        <Line
          yAxisId="left"
          dataKey="rate3m"
          stroke="#F59E0B"
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          connectNulls={true}
          name="3M年率"
        />
        <Line
          yAxisId="right"
          dataKey="price"
          stroke="#9ca3af"
          strokeWidth={1}
          dot={false}
          connectNulls={true}
          name="株価"
        />
        <Legend wrapperStyle={{ fontSize: isMobile ? '0.625rem' : '0.75rem' }} />
        <Tooltip content={<CustomTooltip />} />
      </LineChart>
    </ResponsiveContainer>
  )
}
