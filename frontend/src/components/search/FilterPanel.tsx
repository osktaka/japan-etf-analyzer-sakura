/** Filter panel component for ETF search */
import { useState, useEffect, useMemo } from 'react'
import { Category, Tag, getCategories, getTags, SearchParams } from '../../api'
import { SearchBar } from './SearchBar'
import styles from './FilterPanel.module.css'

/** タググループの表示順序と日本語ラベル */
const TAG_GROUP_ORDER = [
  'region',
  'asset',
  'theme',
  'sector',
  'economic',
  'policy',
] as const

const TAG_GROUP_LABELS: Record<string, string> = {
  theme: 'テーマ',
  region: '地域',
  asset: '資産',
  sector: '業種',
  economic: '経済情勢',
  policy: '政策',
}

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
  compareOnly?: boolean
  onCompareOnlyChange?: (value: boolean) => void
  compareCount?: number
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
  compareOnly = false,
  onCompareOnlyChange,
  compareCount = 0,
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

  /** タグをグループ化し、各グループ内は件数降順でソート */
  const groupedTags = useMemo(() => {
    const groups: Record<string, Tag[]> = {}

    // グループ化（0件タグは除外）
    tags.forEach((tag) => {
      if (tag.etf_count === 0) return
      const category = tag.category || 'other'
      if (!groups[category]) {
        groups[category] = []
      }
      groups[category].push(tag)
    })

    // 各グループ内を件数降順でソート
    Object.keys(groups).forEach((key) => {
      groups[key].sort((a, b) => b.etf_count - a.etf_count)
    })

    return groups
  }, [tags])

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

  const handleTagClick = (id: number, etfCount: number) => {
    // 件数0のタグはクリック不可
    if (etfCount === 0) return

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
    // 検索キーワードもクリア
    onSearch('')
    // 保有中フィルターもクリア
    if (holdingsOnly && onHoldingsOnlyChange) {
      onHoldingsOnlyChange(false)
    }
    // お気に入りフィルターもクリア
    if (favoritesOnly && onFavoritesOnlyChange) {
      onFavoritesOnlyChange(false)
    }
    // 銘柄比較フィルターもクリア
    if (compareOnly && onCompareOnlyChange) {
      onCompareOnlyChange(false)
    }
  }

  const handleHoldingsToggle = () => {
    if (onHoldingsOnlyChange) {
      const newValue = !holdingsOnly
      onHoldingsOnlyChange(newValue)
      // 排他制御: 保有中をONにする場合、他をOFF
      if (newValue) {
        if (favoritesOnly && onFavoritesOnlyChange) {
          onFavoritesOnlyChange(false)
        }
        if (compareOnly && onCompareOnlyChange) {
          onCompareOnlyChange(false)
        }
      }
    }
  }

  const handleFavoritesToggle = () => {
    if (onFavoritesOnlyChange) {
      const newValue = !favoritesOnly
      onFavoritesOnlyChange(newValue)
      // 排他制御: お気に入りをONにする場合、他をOFF
      if (newValue) {
        if (holdingsOnly && onHoldingsOnlyChange) {
          onHoldingsOnlyChange(false)
        }
        if (compareOnly && onCompareOnlyChange) {
          onCompareOnlyChange(false)
        }
      }
    }
  }

  const handleCompareToggle = () => {
    if (onCompareOnlyChange) {
      const newValue = !compareOnly
      onCompareOnlyChange(newValue)
      // 排他制御: 銘柄比較をONにする場合、他をOFF
      if (newValue) {
        if (holdingsOnly && onHoldingsOnlyChange) {
          onHoldingsOnlyChange(false)
        }
        if (favoritesOnly && onFavoritesOnlyChange) {
          onFavoritesOnlyChange(false)
        }
      }
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
        <button
          className={`${styles.categoryBtn} ${compareOnly ? styles.active : ''}`}
          onClick={handleCompareToggle}
          disabled={compareCount === 0}
        >
          銘柄比較({compareCount})
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

      <div className={styles.tagSection}>
        <span className={styles.tagSectionLabel}>タグ:</span>
        <div className={styles.tagGroups}>
          {TAG_GROUP_ORDER.map((groupKey) => {
            const groupTags = groupedTags[groupKey]
            if (!groupTags || groupTags.length === 0) return null

            return (
              <div key={groupKey} className={styles.tagGroupRow}>
                <span className={styles.tagGroupLabel}>
                  {TAG_GROUP_LABELS[groupKey]}:
                </span>
                <div className={styles.tags}>
                  {groupTags.map((tag) => (
                    <button
                      key={tag.id}
                      className={`${styles.tagBtn} ${
                        selectedTags.includes(tag.id) ? styles.active : ''
                      }`}
                      onClick={() => handleTagClick(tag.id, tag.etf_count)}
                    >
                      {tag.name}({tag.etf_count})
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className={styles.searchSection}>
        <SearchBar
          onSearch={onSearch}
          onClear={handleClear}
          placeholder="銘柄コードまたは名前で検索..."
          initialKeyword={initialKeyword}
        />
      </div>
    </div>
  )
}
