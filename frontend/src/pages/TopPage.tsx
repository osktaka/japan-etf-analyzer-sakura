/** Top page component */
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useETFSearch, useCompareList, useFavorites, useAuth } from '../hooks'
import {
  SearchBar,
  SearchResults,
  FilterPanel,
  SortSelector,
} from '../components/search'
import { SearchParams, SortField, SortOrder } from '../api'
import { RecommendSection } from '../components/recommend'
import { ETFDetailModal, LoginPromptModal } from '../components/modal'
import { Pagination } from '../components/common'
import { ROUTES, MAX_COMPARE_ITEMS } from '../utils'
import styles from './TopPage.module.css'

const PAGE_SIZE = 50

export function TopPage() {
  const navigate = useNavigate()
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [currentKeyword, setCurrentKeyword] = useState('')
  const [currentFilters, setCurrentFilters] = useState<SearchParams>({})
  const [currentSort, setCurrentSort] = useState<SortField>('code')
  const [currentOrder, setCurrentOrder] = useState<SortOrder>('asc')
  const [currentPage, setCurrentPage] = useState(1)
  const etfListRef = useRef<HTMLElement>(null)
  const { items, total, isLoading, error, search } = useETFSearch()
  const { count, isInList, toggleCode, canAdd } = useCompareList()
  const { isAuthenticated } = useAuth()
  const { isFavorite, toggleFavorite } = useFavorites()

  useEffect(() => {
    search({ sort: currentSort, order: currentOrder, limit: PAGE_SIZE })
  }, [search, currentSort, currentOrder])

  const handleSearch = (keyword: string) => {
    const trimmed = keyword.trim()
    setCurrentKeyword(trimmed)
    setHasSearched(!!trimmed)
    setCurrentPage(1)
    search({
      ...currentFilters,
      keyword: trimmed || undefined,
      sort: currentSort,
      order: currentOrder,
      limit: PAGE_SIZE,
      offset: 0,
    })
  }

  const handleFilter = (filters: SearchParams) => {
    setCurrentFilters(filters)
    const hasFilters = !!(
      filters.category_id ||
      filters.tag_ids?.length ||
      filters.min_dividend_yield ||
      filters.max_expense_ratio
    )
    setHasSearched(hasFilters || !!currentKeyword)
    setCurrentPage(1)
    search({
      ...filters,
      keyword: currentKeyword || undefined,
      sort: currentSort,
      order: currentOrder,
      limit: PAGE_SIZE,
      offset: 0,
    })
  }

  const handleSortChange = (sort: SortField, order: SortOrder) => {
    setCurrentSort(sort)
    setCurrentOrder(order)
    setCurrentPage(1)
    search({
      ...currentFilters,
      keyword: currentKeyword || undefined,
      sort,
      order,
      limit: PAGE_SIZE,
      offset: 0,
    })
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    search({
      ...currentFilters,
      keyword: currentKeyword || undefined,
      sort: currentSort,
      order: currentOrder,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    })
    etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const handleCompareToggle = (code: string) => {
    if (!isInList(code) && !canAdd) {
      alert(`比較は最大${MAX_COMPARE_ITEMS}件までです`)
      return
    }
    toggleCode(code)
  }

  const handleFavoriteToggle = (code: string) => {
    if (!isAuthenticated) {
      setShowLoginPrompt(true)
      return
    }
    toggleFavorite(code)
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>日本ETF分析</h1>
        <p className={styles.subtitle}>
          ETFを検索・比較して、あなたに最適な投資先を見つけましょう
        </p>
        <div className={styles.searchWrapper}>
          <SearchBar
            onSearch={handleSearch}
            placeholder="銘柄コードまたは名前で検索..."
          />
        </div>
      </section>

      <section className={styles.filterSection}>
        <FilterPanel onFilter={handleFilter} />
      </section>

      <section ref={etfListRef} className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>
            {hasSearched ? '検索結果' : '全銘柄一覧'}
          </h2>
          <SortSelector
            sort={currentSort}
            order={currentOrder}
            onSortChange={handleSortChange}
          />
        </div>
        <SearchResults
          items={items}
          total={total}
          isLoading={isLoading}
          error={error}
          onETFClick={setSelectedCode}
          isInCompare={isInList}
          onCompareToggle={handleCompareToggle}
          isFavorite={isFavorite}
          onFavoriteToggle={handleFavoriteToggle}
        />
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </section>

      <RecommendSection
        onETFClick={setSelectedCode}
        isInCompare={isInList}
        onCompareToggle={handleCompareToggle}
        isFavorite={isFavorite}
        onFavoriteToggle={handleFavoriteToggle}
        onShowAll={() =>
          etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
      />

      {count > 0 && (
        <div className={styles.compareBar}>
          <span>{count}件の銘柄を比較リストに追加中</span>
          <button
            className="btn btn-primary"
            onClick={() => navigate(ROUTES.COMPARE)}
          >
            比較する
          </button>
        </div>
      )}

      <ETFDetailModal
        code={selectedCode}
        onClose={() => setSelectedCode(null)}
        isInCompare={selectedCode ? isInList(selectedCode) : false}
        onCompareToggle={() =>
          selectedCode && handleCompareToggle(selectedCode)
        }
        isFavorite={selectedCode ? isFavorite(selectedCode) : false}
        onFavoriteToggle={() =>
          selectedCode && handleFavoriteToggle(selectedCode)
        }
      />

      <LoginPromptModal
        isOpen={showLoginPrompt}
        onClose={() => setShowLoginPrompt(false)}
      />
    </div>
  )
}
