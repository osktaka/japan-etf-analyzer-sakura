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
]

interface SortSelectorProps {
  sort: SortField
  order: SortOrder
  onSortChange: (sort: SortField, order: SortOrder) => void
}

export function SortSelector({ sort, order, onSortChange }: SortSelectorProps) {
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSortChange(e.target.value as SortField, order)
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
