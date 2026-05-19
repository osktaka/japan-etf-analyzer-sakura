/** Metric table component for displaying ETF metrics */
import { ETFDetail } from '../../api'
import {
  formatPrice,
  formatPercent,
  formatAssets,
  formatDate,
} from '../../utils'
import styles from './MetricTable.module.css'

interface MetricRow {
  label: string
  value: string | null
  highlight?: boolean
  type?: 'positive' | 'negative' | 'neutral'
}

interface MetricTableProps {
  etf: ETFDetail
  compact?: boolean
  showAll?: boolean
}

export function MetricTable({
  etf,
  compact = false,
  showAll = false,
}: MetricTableProps) {
  const getDeviationType = (
    rate: number | null
  ): 'positive' | 'negative' | 'neutral' => {
    if (rate === null) return 'neutral'
    if (rate > 0) return 'positive'
    if (rate < 0) return 'negative'
    return 'neutral'
  }

  const basicMetrics: MetricRow[] = [
    { label: '市場価格', value: formatPrice(etf.market_price) },
    { label: '基準価額', value: formatPrice(etf.nav) },
    {
      label: '分配金利回り',
      value: formatPercent(etf.dividend_yield),
      highlight: true,
    },
    { label: '信託報酬', value: formatPercent(etf.expense_ratio) },
  ]

  const advancedMetrics: MetricRow[] = [
    {
      label: '乖離率',
      value: formatPercent(etf.deviation_rate),
      type: getDeviationType(etf.deviation_rate),
    },
    { label: '純資産総額', value: formatAssets(etf.total_assets) },
    { label: '上場日', value: formatDate(etf.listing_date) },
  ]

  const metrics = showAll ? [...basicMetrics, ...advancedMetrics] : basicMetrics

  const getValueClassName = (row: MetricRow): string => {
    const classes: string[] = []
    if (row.highlight) classes.push(styles.highlight)
    if (row.type === 'positive') classes.push(styles.positive)
    if (row.type === 'negative') classes.push(styles.negative)
    return classes.join(' ')
  }

  return (
    <table className={`${styles.table} ${compact ? styles.compact : ''}`}>
      <tbody>
        {metrics.map((row) => (
          <tr key={row.label}>
            <th>{row.label}</th>
            <td className={getValueClassName(row)}>{row.value || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
