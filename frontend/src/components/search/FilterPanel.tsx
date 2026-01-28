/** Filter panel component for ETF search */
import { useState, useEffect } from 'react'
import { Category, Tag, getCategories, getTags, SearchParams } from '../../api'
import { SearchBar } from './SearchBar'
import styles from './FilterPanel.module.css'

interface FilterPanelProps {
  onFilter: (params: SearchParams) => void
  onSearch: (keyword: string) => void
  initialParams?: SearchParams
  initialKeyword?: string
  holdingsOnly?: boolean
  onHoldingsOnlyChange?: (value: boolean) => void
  holdingsCount?: number
  favoritesOnly?: boolean
  onFavoritesOnlyChange?: (value: boolean) => void
  favoritesCount?: number
}

export function FilterPanel({
  onFilter,
  onSearch,
  initialParams = {},
  initialKeyword = '',
  holdingsOnly = false,
  onHoldingsOnlyChange,
  holdingsCount = 0,
  favoritesOnly = false,
  onFavoritesOnlyChange,
  favoritesCount = 0,
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

  // 親からのパラメータ変更（ブラウザバック等）を反映
  // 各プロパティを個別に依存配列に指定して無限ループを防止
  useEffect(() => {
    setSelectedCategory(initialParams.category_id || null)
    setSelectedTags(initialParams.tag_ids || [])
  }, [initialParams.category_id, initialParams.tag_ids])

  // フィルタ適用ロジック
  const applyFilters = (cat: number | null, tgs: number[]) => {
    const params: SearchParams = {}
    if (cat) params.category_id = cat
    if (tgs.length > 0) params.tag_ids = tgs
    onFilter(params)
  }

  // カテゴリ・タグ変更時は即時反映
  const handleCategoryClick = (id: number) => {
    const newCat = selectedCategory === id ? null : id
    setSelectedCategory(newCat)
    applyFilters(newCat, selectedTags)
  }

  const handleTagClick = (id: number) => {
    const newTags = selectedTags.includes(id)
      ? selectedTags.filter((t) => t !== id)
      : [...selectedTags, id]
    setSelectedTags(newTags)
    applyFilters(selectedCategory, newTags)
  }

  const handleClear = () => {
    setSelectedCategory(null)
    setSelectedTags([])
    onFilter({})
    // 保有中フィルターもクリア
    if (holdingsOnly && onHoldingsOnlyChange) {
      onHoldingsOnlyChange(false)
    }
    // お気に入りフィルターもクリア
    if (favoritesOnly && onFavoritesOnlyChange) {
      onFavoritesOnlyChange(false)
    }
  }

  const handleHoldingsToggle = () => {
    if (onHoldingsOnlyChange) {
      onHoldingsOnlyChange(!holdingsOnly)
    }
  }

  const handleFavoritesToggle = () => {
    if (onFavoritesOnlyChange) {
      onFavoritesOnlyChange(!favoritesOnly)
    }
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

      <div className={styles.section}>
        <button
          className={`${styles.categoryBtn} ${holdingsOnly ? styles.active : ''}`}
          onClick={handleHoldingsToggle}
        >
          保有中({holdingsCount})
        </button>
        <button
          className={`${styles.categoryBtn} ${favoritesOnly ? styles.active : ''}`}
          onClick={handleFavoritesToggle}
        >
          お気に入り({favoritesCount})
        </button>
      </div>

      <div className={styles.inlineSection}>
        <span className={styles.inlineLabel}>カテゴリ:</span>
        <div className={styles.categories}>
          {categories.map((cat) => (
            <button
              key={cat.id}
              className={`${styles.categoryBtn} ${
                selectedCategory === cat.id ? styles.active : ''
              }`}
              onClick={() => handleCategoryClick(cat.id)}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.inlineSection}>
        <span className={styles.inlineLabel}>タグ:</span>
        <div className={styles.tags}>
          {tags.map((tag) => (
            <button
              key={tag.id}
              className={`${styles.tagBtn} ${
                selectedTags.includes(tag.id) ? styles.active : ''
              }`}
              onClick={() => handleTagClick(tag.id)}
            >
              {tag.name}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.searchSection}>
        <SearchBar
          onSearch={onSearch}
          placeholder="銘柄コードまたは名前で検索..."
          initialKeyword={initialKeyword}
        />
      </div>
    </div>
  )
}
