/** Top page component */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useETFSearch, useCompareList, useFavorites, useAuth } from '../hooks'
import {
  SearchResults,
  FilterPanel,
  SortSelector,
  ETFTableView,
  ViewModeToggle,
  PeriodSelector,
} from '../components/search'
import type { ViewMode } from '../components/search'
import {
  SearchParams,
  SortField,
  SortOrder,
  getBatchPerformance,
  BatchPerformanceData,
  PerformancePeriod,
} from '../api'
import { RecommendSection } from '../components/recommend'
import { ETFDetailModal, LoginPromptModal } from '../components/modal'
import { Pagination } from '../components/common'
import { ROUTES, MAX_COMPARE_ITEMS } from '../utils'
import styles from './TopPage.module.css'

const PAGE_SIZE = 50

export function TopPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // URLパラメータから初期状態を復元
  const getInitialFilters = (): SearchParams => {
    const filters: SearchParams = {}
    const cat = searchParams.get('category')
    const tags = searchParams.get('tags')
    const minD = searchParams.get('min_dividend')
    const maxE = searchParams.get('max_expense')

    if (cat) filters.category_id = Number(cat)
    if (tags) filters.tag_ids = tags.split(',').map(Number)
    if (minD) filters.min_dividend_yield = Number(minD)
    if (maxE) filters.max_expense_ratio = Number(maxE)
    return filters
  }

  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // 表示モード
  const [viewMode, setViewMode] = useState<ViewMode>(
    (searchParams.get('view') as ViewMode) || 'card'
  )
  const [performance, setPerformance] = useState<BatchPerformanceData>({})
  const [selectedPeriods, setSelectedPeriods] = useState<PerformancePeriod[]>([
    '6m',
    '1y',
    '3y',
  ])

  // おすすめタブの状態
  const [recommendTab, setRecommendTab] = useState(
    searchParams.get('tab') || 'popular'
  )

  const [currentKeyword, setCurrentKeyword] = useState(
    searchParams.get('q') || ''
  )
  const [currentFilters, setCurrentFilters] =
    useState<SearchParams>(getInitialFilters())
  const [currentSort, setCurrentSort] = useState<SortField>(
    (searchParams.get('sort') as SortField) || 'code'
  )
  const [currentOrder, setCurrentOrder] = useState<SortOrder>(
    (searchParams.get('order') as SortOrder) || 'asc'
  )
  const [currentPage, setCurrentPage] = useState(
    Number(searchParams.get('page')) || 1
  )

  const etfListRef = useRef<HTMLElement>(null)
  const { items, total, isLoading, error, search } = useETFSearch()
  const { count, isInList, toggleCode, canAdd } = useCompareList()
  const { isAuthenticated } = useAuth()
  const { isFavorite, toggleFavorite } = useFavorites()

  // 表形式表示時にパフォーマンスデータを取得
  useEffect(() => {
    if (viewMode === 'table' && items.length > 0) {
      const codes = items.map((item) => item.code)
      getBatchPerformance(codes).then(setPerformance)
    }
  }, [viewMode, items])

  // URLパラメータ更新ヘルパー
  const updateURL = useCallback(
    (
      params: Partial<{
        tab: string
        q: string
        sort: string
        order: string
        page: string
        category: string
        tags: string
        min_dividend: string
        max_expense: string
        view: string
      }>
    ) => {
      setSearchParams(
        (prev) => {
          const newParams = new URLSearchParams(prev)
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              newParams.set(key, value)
            } else {
              newParams.delete(key)
            }
          })
          return newParams
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  useEffect(() => {
    // 初回マウント時、URLパラメータがあれば検索を実行
    const filters = getInitialFilters()
    const keyword = searchParams.get('q') || undefined
    const sort = (searchParams.get('sort') as SortField) || 'code'
    const order = (searchParams.get('order') as SortOrder) || 'asc'
    const page = Number(searchParams.get('page')) || 1

    // フィルタ条件があるか判定
    const hasInitFilters = !!(
      filters.category_id ||
      filters.tag_ids?.length ||
      filters.min_dividend_yield ||
      filters.max_expense_ratio
    )

    if (keyword || hasInitFilters) {
      setHasSearched(true)
    }

    search({
      ...filters,
      keyword,
      sort,
      order,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    })
    // eslint-disable-next-line
  }, []) // 初回のみ実行

  const handleRecommendTabChange = (tab: string) => {
    setRecommendTab(tab)
    updateURL({ tab })
  }

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode)
    updateURL({ view: mode === 'card' ? undefined : mode })
  }

  const handleSearch = (keyword: string) => {
    const trimmed = keyword.trim()
    setCurrentKeyword(trimmed)
    setHasSearched(!!trimmed)
    setCurrentPage(1)

    updateURL({
      q: trimmed,
      page: '1',
    })

    search({
      ...currentFilters,
      keyword: trimmed || undefined,
      sort: currentSort,
      order: currentOrder,
      limit: PAGE_SIZE,
      offset: 0,
    })

    etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleFilter = useCallback(
    (filters: SearchParams) => {
      setCurrentFilters(filters)
      const hasFilters = !!(
        filters.category_id ||
        filters.tag_ids?.length ||
        filters.min_dividend_yield ||
        filters.max_expense_ratio
      )
      setHasSearched(hasFilters || !!currentKeyword)
      setCurrentPage(1)

      updateURL({
        category: filters.category_id?.toString(),
        tags: filters.tag_ids?.join(','),
        min_dividend: filters.min_dividend_yield?.toString(),
        max_expense: filters.max_expense_ratio?.toString(),
        page: '1',
      })

      search({
        ...filters,
        keyword: currentKeyword || undefined,
        sort: currentSort,
        order: currentOrder,
        limit: PAGE_SIZE,
        offset: 0,
      })
    },
    [currentKeyword, currentSort, currentOrder, search, updateURL]
  )

  const handleSortChange = (sort: SortField, order: SortOrder) => {
    setCurrentSort(sort)
    setCurrentOrder(order)
    setCurrentPage(1)

    updateURL({
      sort,
      order,
      page: '1',
    })

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

    updateURL({
      page: page.toString(),
    })

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
      </section>

      {/* おすすめセクションを上部に移動 */}
      <RecommendSection
        onETFClick={setSelectedCode}
        isInCompare={isInList}
        onCompareToggle={handleCompareToggle}
        isFavorite={isFavorite}
        onFavoriteToggle={handleFavoriteToggle}
        onShowAll={() =>
          etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
        selectedPerspective={recommendTab}
        onSelectPerspective={handleRecommendTabChange}
      />

      {/* 検索・一覧セクション */}
      <section ref={etfListRef} className={styles.section}>
        <div className={styles.searchHeader}>
          <h2 className={styles.searchTitle}>銘柄を探す</h2>
        </div>

        <div className={styles.filterSection}>
          <FilterPanel
            onFilter={handleFilter}
            onSearch={handleSearch}
            initialParams={currentFilters}
            initialKeyword={currentKeyword}
          />
        </div>

        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>
            {hasSearched ? '検索結果' : '全銘柄一覧'}
          </h2>
          <div className={styles.sectionControls}>
            <ViewModeToggle mode={viewMode} onChange={handleViewModeChange} />
            {viewMode === 'card' ? (
              <SortSelector
                sort={currentSort}
                order={currentOrder}
                onSortChange={handleSortChange}
              />
            ) : (
              <PeriodSelector
                selectedPeriods={selectedPeriods}
                onChange={setSelectedPeriods}
              />
            )}
          </div>
        </div>
        <div className={styles.resultCount}>
          <span>{total}件</span>
        </div>
        {viewMode === 'card' ? (
          <SearchResults
            items={items}
            isLoading={isLoading}
            error={error}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
          />
        ) : (
          <ETFTableView
            items={items}
            performance={performance}
            selectedPeriods={selectedPeriods}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
          />
        )}
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </section>

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
