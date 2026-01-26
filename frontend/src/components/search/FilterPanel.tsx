/** Filter panel component for ETF search */
import { useState, useEffect } from 'react'
import { Category, Tag, getCategories, getTags, SearchParams } from '../../api'
import { SearchBar } from './SearchBar'
import styles from './FilterPanel.module.css'

interface FilterPanelProps {
  onFilter: (params: SearchParams) => void
  onSearch: (keyword: string) => void
  initialParams?: SearchParams
}

export function FilterPanel({
  onFilter,
  onSearch,
  initialParams = {},
}: FilterPanelProps) {
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<number | null>(
    initialParams.category_id || null
  )
  const [selectedTags, setSelectedTags] = useState<number[]>(
    initialParams.tag_ids || []
  )
  const [minDividend, setMinDividend] = useState<string>(
    initialParams.min_dividend_yield?.toString() || ''
  )
  const [maxExpense, setMaxExpense] = useState<string>(
    initialParams.max_expense_ratio?.toString() || ''
  )

  useEffect(() => {
    const loadFilters = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [cats, tgs] = await Promise.all([getCategories(), getTags()])
        setCategories(cats)
        setTags(tgs)
      } catch {
        setError('フィルター情報の取得に失敗しました')
      } finally {
        setIsLoading(false)
      }
    }
    loadFilters()
  }, [])

  // フィルタ適用ロジック
  const applyFilters = (
    cat: number | null,
    tgs: number[],
    minD: string,
    maxE: string
  ) => {
    const params: SearchParams = {}
    if (cat) params.category_id = cat
    if (tgs.length > 0) params.tag_ids = tgs
    if (minD) params.min_dividend_yield = parseFloat(minD)
    if (maxE) params.max_expense_ratio = parseFloat(maxE)
    onFilter(params)
  }

  // カテゴリ・タグ変更時は即時反映
  const handleCategoryClick = (id: number) => {
    const newCat = selectedCategory === id ? null : id
    setSelectedCategory(newCat)
    applyFilters(newCat, selectedTags, minDividend, maxExpense)
  }

  const handleTagClick = (id: number) => {
    const newTags = selectedTags.includes(id)
      ? selectedTags.filter((t) => t !== id)
      : [...selectedTags, id]
    setSelectedTags(newTags)
    applyFilters(selectedCategory, newTags, minDividend, maxExpense)
  }

  // 数値入力の変更検知（デバウンス）
  // 意図的にminDividend, maxExpenseのみをトリガーとする
  useEffect(() => {
    const timer = setTimeout(() => {
      applyFilters(selectedCategory, selectedTags, minDividend, maxExpense)
    }, 500)

    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minDividend, maxExpense])

  const handleClear = () => {
    setSelectedCategory(null)
    setSelectedTags([])
    setMinDividend('')
    setMaxExpense('')
    onFilter({})
  }

  if (isLoading) {
    return <div className={styles.panel}>読み込み中...</div>
  }

  if (error) {
    return <div className={styles.panel}>{error}</div>
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3 className={styles.title}>絞り込み</h3>
        <button className={styles.clearBtn} onClick={handleClear}>
          クリア
        </button>
      </div>

      <div className={styles.searchSection}>
        <SearchBar
          onSearch={onSearch}
          placeholder="銘柄コードまたは名前で検索..."
        />
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>カテゴリ</div>
        <div className={styles.categories}>
          {categories.map((cat) => (
            <button
              key={cat.id}
              className={`${styles.categoryBtn} ${selectedCategory === cat.id ? styles.active : ''
                }`}
              onClick={() => handleCategoryClick(cat.id)}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>タグ</div>
        <div className={styles.tags}>
          {tags.map((tag) => (
            <button
              key={tag.id}
              className={`${styles.tagBtn} ${selectedTags.includes(tag.id) ? styles.active : ''
                }`}
              onClick={() => handleTagClick(tag.id)}
            >
              {tag.name}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>配当利回り・信託報酬</div>
        <div className={styles.rangeInputs}>
          <div className={styles.rangeGroup}>
            <label>配当利回り（%以上）</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={minDividend}
              onChange={(e) => setMinDividend(e.target.value)}
              placeholder="例: 3.0"
            />
          </div>
          <div className={styles.rangeGroup}>
            <label>信託報酬（%以下）</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={maxExpense}
              onChange={(e) => setMaxExpense(e.target.value)}
              placeholder="例: 0.5"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
