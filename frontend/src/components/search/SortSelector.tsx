/** Sort selector component */
import { SortField, SortOrder } from '../../api'
import styles from './SortSelector.module.css'

interface SortOption {
  value: SortField
  label: string
}

const SORT_OPTIONS: SortOption[] = [
  { value: 'code', label: '銘柄コード' },
  { value: 'name', label: '銘柄名' },
  { value: 'dividend_yield', label: '配当利回り' },
  { value: 'expense_ratio', label: '信託報酬' },
  { value: 'total_assets', label: '純資産総額' },
  { value: 'score_balance', label: 'スコア（総合）' },
  { value: 'score_dividend', label: 'スコア（配当）' },
  { value: 'score_low_cost', label: 'スコア（コスト）' },
  { value: 'score_stability', label: 'スコア（安定）' },
  { value: 'score_volume', label: 'スコア（取引）' },
  { value: 'score_growth', label: 'スコア（成長）' },
  { value: 'axis_dividend_power', label: '- 配当力' },
  { value: 'axis_cost_efficiency', label: '- コスト' },
  { value: 'axis_scale_reliability', label: '- 安定性' },
  { value: 'axis_trading_quality', label: '- 取引規模' },
  { value: 'axis_return_performance', label: '- リターン' },
]

interface SortSelectorProps {
  sort: SortField
  order: SortOrder
  onSortChange: (sort: SortField, order: SortOrder) => void
}

// 低い値が良い項目（これ以外は降順がデフォルト）
const LOW_IS_BETTER: SortField[] = ['expense_ratio']
const NEUTRAL: SortField[] = ['code', 'name']

export function SortSelector({ sort, order, onSortChange }: SortSelectorProps) {
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSort = e.target.value as SortField
    // コード・名前は現在のorder維持、信託報酬は昇順、それ以外は降順
    let newOrder: SortOrder = order
    if (LOW_IS_BETTER.includes(newSort)) {
      newOrder = 'asc'
    } else if (!NEUTRAL.includes(newSort)) {
      newOrder = 'desc'
    }
    onSortChange(newSort, newOrder)
  }

  const handleOrderToggle = () => {
    onSortChange(sort, order === 'asc' ? 'desc' : 'asc')
  }

  return (
    <div className={styles.container}>
      <label className={styles.label}>並び替え:</label>
      <select
        className={styles.select}
        value={sort}
        onChange={handleSortChange}
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={styles.orderButton}
        onClick={handleOrderToggle}
        title={order === 'asc' ? '昇順' : '降順'}
      >
        {order === 'asc' ? '↑' : '↓'}
      </button>
    </div>
  )
}
