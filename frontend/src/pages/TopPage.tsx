/** Top page component */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  useETFSearch,
  useCompareList,
  useFavorites,
  useAuth,
  usePortfolio,
  useTopPageStorage,
} from '../hooks'
import {
  SearchResults,
  FilterPanel,
  SortSelector,
  ETFTableView,
  ViewModeToggle,
  PeriodSelector,
  ReturnTypeToggle,
  TableDisplayToggle,
  ScoringModeToggle,
  PerspectiveSelector,
} from '../components/search'
import type {
  ViewMode,
  ReturnType,
  DisplayMode,
  PerspectiveKey,
  ScoringMode,
} from '../components/search'
import {
  SearchParams,
  SortField,
  SortOrder,
  getBatchPerformance,
  getBatchScores,
  PerformancePeriod,
  BatchPerformanceData,
  BatchScoreData,
} from '../api'
import { RecommendSection } from '../components/recommend'
import { ETFDetailModal, LoginPromptModal } from '../components/modal'
import { Pagination } from '../components/common'
import { MAX_COMPARE_ITEMS, buildSearchParams } from '../utils'
import styles from './TopPage.module.css'

const PAGE_SIZE = 50

// 切り口からソートフィールドへのマッピング（共通定義）
const PERSPECTIVE_TO_SORT_FIELD: Record<PerspectiveKey, SortField> = {
  balance: 'score_balance',
  dividend: 'score_dividend',
  'low-cost': 'score_low_cost',
  stability: 'score_stability',
  volume: 'score_volume',
  growth: 'score_growth',
}

export function TopPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const storage = useTopPageStorage()

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

  // 表示モードの初期値を取得（ソート初期化で参照するため）
  const getInitialViewMode = (): ViewMode => {
    const urlView = searchParams.get('view') as ViewMode
    if (urlView) return urlView
    const storedView = storage.getStoredViewMode()
    return storedView || 'card'
  }

  // 表示モード（URL優先 → localStorage → デフォルト）
  const [viewMode, setViewMode] = useState<ViewMode>(getInitialViewMode)
  const [performance, setPerformance] = useState<BatchPerformanceData>({})
  const [scores, setScores] = useState<BatchScoreData>({})
  const [selectedPeriods, setSelectedPeriods] = useState<PerformancePeriod[]>(
    storage.getStoredPeriods
  )
  const [returnType, setReturnType] = useState<ReturnType>(
    storage.getStoredReturnType()
  )
  const [displayMode, setDisplayMode] = useState<DisplayMode>(
    storage.getStoredDisplayMode()
  )
  const [scoringMode, setScoringMode] = useState<ScoringMode>(() => {
    const saved = localStorage.getItem('scoringMode')
    return (saved === 'partial' ? 'partial' : 'full') as ScoringMode
  })
  const [selectedPerspective, setSelectedPerspective] =
    useState<PerspectiveKey>(storage.getStoredPerspective())

  // おすすめタブの状態
  const [recommendTab, setRecommendTab] = useState(
    searchParams.get('tab') || 'balance'
  )

  const [currentKeyword, setCurrentKeyword] = useState(
    searchParams.get('q') || ''
  )
  const [currentFilters, setCurrentFilters] =
    useState<SearchParams>(getInitialFilters())

  // ソート状態（URL優先 → localStorage → デフォルト）
  // 表形式かつスコア表示: score_balance desc
  // 表形式かつ傾向表示: return_1y desc
  // カード形式: return_1y desc
  const [currentSort, setCurrentSort] = useState<SortField>(() => {
    const urlSort = searchParams.get('sort') as SortField
    if (urlSort) return urlSort
    const initialViewMode = getInitialViewMode()
    const initialDisplayMode = storage.getStoredDisplayMode()
    // カード形式の場合
    if (initialViewMode === 'card') {
      const storedSort = storage.getStoredCardSort()
      return storedSort.sort
    }
    // 表形式かつスコア表示の場合
    if (initialDisplayMode === 'score') {
      const storedSort = storage.getStoredScoreSort()
      const initialPerspective = storage.getStoredPerspective()
      // evaluation_score または score_*ソート時は選択中の切り口を反映
      if (
        storedSort.sort === 'evaluation_score' ||
        storedSort.sort.startsWith('score_')
      ) {
        return PERSPECTIVE_TO_SORT_FIELD[initialPerspective]
      }
      return storedSort.sort
    }
    // 表形式かつ傾向表示の場合
    const storedSort = storage.getStoredTrendSort()
    return storedSort.sort
  })
  const [currentOrder, setCurrentOrder] = useState<SortOrder>(() => {
    const urlOrder = searchParams.get('order') as SortOrder
    if (urlOrder) return urlOrder
    const initialViewMode = getInitialViewMode()
    const initialDisplayMode = storage.getStoredDisplayMode()
    // カード形式の場合
    if (initialViewMode === 'card') {
      const storedSort = storage.getStoredCardSort()
      return storedSort.order
    }
    // 表形式かつスコア表示の場合
    if (initialDisplayMode === 'score') {
      const storedSort = storage.getStoredScoreSort()
      return storedSort.order
    }
    // 表形式かつ傾向表示の場合
    const storedSort = storage.getStoredTrendSort()
    return storedSort.order
  })
  const [currentPage, setCurrentPage] = useState(
    Number(searchParams.get('page')) || 1
  )

  const etfListRef = useRef<HTMLElement>(null)
  const isInitialMount = useRef(true)
  const isScoringModeInitialMount = useRef(true)
  const isReturnTypeInitialMount = useRef(true)
  const isPerspectiveInitialMount = useRef(true)
  const prevDisplayModeRef = useRef<DisplayMode>(displayMode)
  const prevViewModeRef = useRef<ViewMode>(viewMode)
  const { items, total, isLoading, error, search } = useETFSearch()
  const {
    isInList,
    toggleCode,
    canAdd,
    codes: compareCodes,
    count: compareCount,
  } = useCompareList()
  const { isAuthenticated } = useAuth()
  const { isFavorite, toggleFavorite, favoriteCodes } = useFavorites()
  const { holdings } = usePortfolio()
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [holdingsOnly, setHoldingsOnly] = useState(false)
  const [compareOnly, setCompareOnly] = useState(false)

  // 保有コードのSetを作成（quantity > 0の銘柄のみ）
  const holdingCodes = useMemo(
    () =>
      new Set(holdings.filter((h) => h.quantity > 0).map((h) => h.etf_code)),
    [holdings]
  )

  // isHolding関数 - ETFCard/ETFTableViewに渡すために使用
  const isHolding = (code: string): boolean => holdingCodes.has(code)

  // 表形式表示時にパフォーマンスデータまたはスコアデータを取得
  useEffect(() => {
    if (viewMode === 'table' && items.length > 0) {
      const codes = items.map((item) => item.code)
      if (displayMode === 'trend') {
        getBatchPerformance(codes).then((data) => {
          setPerformance(data)
        })
      } else if (displayMode === 'score') {
        getBatchScores(codes, scoringMode).then((data) => {
          setScores(data)
        })
      }
    }
  }, [viewMode, items, displayMode, scoringMode])

  // 表示期間をローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(
      storage.keys.PERIODS_STORAGE_KEY,
      JSON.stringify(selectedPeriods)
    )
  }, [selectedPeriods, storage.keys.PERIODS_STORAGE_KEY])

  // 切り口をローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(
      storage.keys.PERSPECTIVE_STORAGE_KEY,
      selectedPerspective
    )
  }, [selectedPerspective, storage.keys.PERSPECTIVE_STORAGE_KEY])

  // 上昇率タイプをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(storage.keys.RETURN_TYPE_STORAGE_KEY, returnType)
  }, [returnType, storage.keys.RETURN_TYPE_STORAGE_KEY])

  // 表示モードをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(storage.keys.VIEW_MODE_STORAGE_KEY, viewMode)
  }, [viewMode, storage.keys.VIEW_MODE_STORAGE_KEY])

  // viewMode変更時にソート状態を保存・復元
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isInitialMount.current) {
      return
    }

    // 前回のviewModeのソート状態を保存（prevViewModeRef.currentは前のviewModeを指している）
    storage.saveSortState(
      prevViewModeRef.current,
      displayMode,
      currentSort,
      currentOrder
    )

    // URLのsort/orderをクリア（localStorage復元を優先）
    setSearchParams(
      (prev) => {
        const newParams = new URLSearchParams(prev)
        newParams.delete('sort')
        newParams.delete('order')
        return newParams
      },
      { replace: true }
    )

    // 前回のviewModeを新しい値で更新（次回の保存に備える）
    prevViewModeRef.current = viewMode

    // 新しいviewModeのソート状態を復元
    let storedSort: { sort: SortField; order: SortOrder }
    if (viewMode === 'card') {
      storedSort = storage.getStoredCardSort()
    } else if (displayMode === 'score') {
      storedSort = storage.getStoredScoreSort()
    } else {
      storedSort = storage.getStoredTrendSort()
    }

    const newSort = storedSort.sort
    const newOrder = storedSort.order

    setCurrentSort(newSort)
    setCurrentOrder(newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== currentSort || newOrder !== currentOrder) {
      const searchParams = buildSearchParams({
        currentFilters,
        currentKeyword,
        currentSort: newSort,
        currentOrder: newOrder,
        currentPage,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(searchParams)
    }
    // viewMode変更時のみ実行（他の依存は意図的に除外）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode])

  // returnType変更時にパフォーマンスソート中なら一覧を再取得
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isReturnTypeInitialMount.current) {
      isReturnTypeInitialMount.current = false
      return
    }

    // パフォーマンスソートのフィールドか判定
    const isPerformanceSort = [
      'return_1m',
      'return_3m',
      'return_6m',
      'return_1y',
      'return_3y',
      'return_5y',
      'return_10y',
      'return_20y',
    ].includes(currentSort)

    if (isPerformanceSort) {
      const searchParams = buildSearchParams({
        currentFilters,
        currentKeyword,
        currentSort,
        currentOrder,
        currentPage,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(searchParams)
    }
    // returnType変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [returnType])

  // 表示モードをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(storage.keys.DISPLAY_MODE_STORAGE_KEY, displayMode)
  }, [displayMode, storage.keys.DISPLAY_MODE_STORAGE_KEY])

  // scoringMode変更時にスコアソート中なら一覧を再取得
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isScoringModeInitialMount.current) {
      isScoringModeInitialMount.current = false
      return
    }

    // スコアソートのフィールドか判定
    const isScoreSort = currentSort.startsWith('score_')

    if (isScoreSort) {
      const searchParams = buildSearchParams({
        currentFilters,
        currentKeyword,
        currentSort,
        currentOrder,
        currentPage,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(searchParams)
    }
    // scoringMode変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoringMode])

  // selectedPerspective変更時にevaluation_scoreソート中なら対応する切り口でソート
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isPerspectiveInitialMount.current) {
      isPerspectiveInitialMount.current = false
      return
    }

    // evaluation_score または score_*でソート中なら対応するperspectiveソートに変更してAPI再取得
    const isScoreSort =
      currentSort === 'evaluation_score' || currentSort.startsWith('score_')

    if (isScoreSort) {
      const newSort = PERSPECTIVE_TO_SORT_FIELD[selectedPerspective]
      setCurrentSort(newSort)

      // ソート変更でsearch()を実行
      const searchParams = buildSearchParams({
        currentFilters,
        currentKeyword,
        currentSort: newSort,
        currentOrder,
        currentPage,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(searchParams)
    }
    // selectedPerspective変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPerspective])

  // displayMode変更時にソート状態を保存・復元
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isInitialMount.current) {
      return
    }

    // 前回のモードのソート状態を保存（prevDisplayModeRef.currentは前のdisplayModeを指している）
    storage.saveSortState(
      viewMode,
      prevDisplayModeRef.current,
      currentSort,
      currentOrder
    )

    // URLのsort/orderをクリア（localStorage復元を優先）
    setSearchParams(
      (prev) => {
        const newParams = new URLSearchParams(prev)
        newParams.delete('sort')
        newParams.delete('order')
        return newParams
      },
      { replace: true }
    )

    // 前回のdisplayModeを新しい値で更新（次回の保存に備える）
    prevDisplayModeRef.current = displayMode

    // 新しいdisplayModeに応じたソート状態を復元
    const storedSort =
      displayMode === 'score'
        ? storage.getStoredScoreSort()
        : storage.getStoredTrendSort()

    const newSort = storedSort.sort
    const newOrder = storedSort.order

    setCurrentSort(newSort)
    setCurrentOrder(newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== currentSort || newOrder !== currentOrder) {
      const searchParams = buildSearchParams({
        currentFilters,
        currentKeyword,
        currentSort: newSort,
        currentOrder: newOrder,
        currentPage,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(searchParams)
    }
    // displayMode変更時のみ実行（他の依存は意図的に除外）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayMode])

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
    const initialViewMode = getInitialViewMode()
    const initialDisplayMode = storage.getStoredDisplayMode()

    // URLパラメータ優先、なければviewMode/displayModeに応じたデフォルト
    let sort: SortField
    let order: SortOrder

    if (searchParams.get('sort')) {
      sort = searchParams.get('sort') as SortField
      order = (searchParams.get('order') as SortOrder) || 'desc'
    } else if (initialViewMode === 'card') {
      const storedSort = storage.getStoredCardSort()
      sort = storedSort.sort
      order = storedSort.order
    } else if (initialDisplayMode === 'score') {
      const storedSort = storage.getStoredScoreSort()
      const initialPerspective = storage.getStoredPerspective()
      // evaluation_score または score_*ソート時は選択中の切り口を反映
      if (
        storedSort.sort === 'evaluation_score' ||
        storedSort.sort.startsWith('score_')
      ) {
        sort = PERSPECTIVE_TO_SORT_FIELD[initialPerspective]
      } else {
        sort = storedSort.sort
      }
      order = storedSort.order
    } else {
      const storedSort = storage.getStoredTrendSort()
      sort = storedSort.sort
      order = storedSort.order
    }

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
      return_type: returnType,
      scoring_mode: scoringMode,
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

    const searchParams = buildSearchParams({
      currentFilters,
      currentKeyword: trimmed,
      currentSort,
      currentOrder,
      currentPage: 1,
      returnType,
      scoringMode,
      pageSize: PAGE_SIZE,
      favoritesOnly,
      holdingsOnly,
      compareOnly,
      favoriteCodes,
      holdingCodes,
      compareCodes,
    })

    search(searchParams)

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

      const searchParams = buildSearchParams({
        currentFilters: filters,
        currentKeyword,
        currentSort,
        currentOrder,
        currentPage: 1,
        returnType,
        scoringMode,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })

      search(searchParams)
    },
    [
      currentKeyword,
      currentSort,
      currentOrder,
      returnType,
      scoringMode,
      search,
      updateURL,
      favoritesOnly,
      favoriteCodes,
      holdingsOnly,
      holdingCodes,
      compareOnly,
      compareCodes,
    ]
  )

  const handleSortChange = (sort: SortField, order: SortOrder) => {
    setCurrentSort(sort)
    setCurrentOrder(order)
    setCurrentPage(1)

    // ソート状態をローカルストレージに保存
    storage.saveSortState(viewMode, displayMode, sort, order)

    updateURL({
      sort,
      order,
      page: '1',
    })

    const searchParams = buildSearchParams({
      currentFilters,
      currentKeyword,
      currentSort: sort,
      currentOrder: order,
      currentPage: 1,
      returnType,
      scoringMode,
      pageSize: PAGE_SIZE,
      favoritesOnly,
      holdingsOnly,
      compareOnly,
      favoriteCodes,
      holdingCodes,
      compareCodes,
    })

    search(searchParams)
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)

    updateURL({
      page: page.toString(),
    })

    const searchParams = buildSearchParams({
      currentFilters,
      currentKeyword,
      currentSort,
      currentOrder,
      currentPage: page,
      returnType,
      scoringMode,
      pageSize: PAGE_SIZE,
      favoritesOnly,
      holdingsOnly,
      compareOnly,
      favoriteCodes,
      holdingCodes,
      compareCodes,
    })

    search(searchParams)
    etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // お気に入り/保有中フィルター状態が変わったときに検索を実行
  useEffect(() => {
    // 初回マウント時はスキップ（初回検索は別のuseEffectで実行済み）
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    setCurrentPage(1)

    const params = buildSearchParams({
      currentFilters,
      currentKeyword,
      currentSort,
      currentOrder,
      currentPage: 1,
      returnType,
      scoringMode,
      pageSize: PAGE_SIZE,
      favoritesOnly,
      holdingsOnly,
      compareOnly,
      favoriteCodes,
      holdingCodes,
      compareCodes,
    })

    search(params)
    // favoritesOnly/holdingsOnly/compareOnly変更時のみ発動
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [favoritesOnly, holdingsOnly, compareOnly])

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

  // お気に入りフィルター変更ハンドラ（未ログイン時はログイン促進）
  const handleFavoritesOnlyChange = (value: boolean) => {
    if (!isAuthenticated) {
      setShowLoginPrompt(true)
      return
    }
    setFavoritesOnly(value)
  }

  // 保有中フィルター変更ハンドラ（未ログイン時はログイン促進）
  const handleHoldingsOnlyChange = (value: boolean) => {
    if (!isAuthenticated) {
      setShowLoginPrompt(true)
      return
    }
    setHoldingsOnly(value)
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>東証ETF銘柄の比較分析</h1>
        <p className={styles.subtitle}>
          銘柄を検索・比較して、あなたに最適な投資先を見つけましょう
        </p>
      </section>

      {/* おすすめセクションを上部に移動 */}
      <RecommendSection
        onETFClick={setSelectedCode}
        isInCompare={isInList}
        onCompareToggle={handleCompareToggle}
        isFavorite={isFavorite}
        onFavoriteToggle={handleFavoriteToggle}
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
            holdingsOnly={holdingsOnly}
            onHoldingsOnlyChange={handleHoldingsOnlyChange}
            holdingsCount={holdingCodes.size}
            favoritesOnly={favoritesOnly}
            onFavoritesOnlyChange={handleFavoritesOnlyChange}
            favoritesCount={favoriteCodes.size}
            compareOnly={compareOnly}
            onCompareOnlyChange={setCompareOnly}
            compareCount={compareCount}
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
              <>
                <TableDisplayToggle
                  displayMode={displayMode}
                  onChange={setDisplayMode}
                />
                {displayMode === 'score' && (
                  <>
                    <ScoringModeToggle
                      scoringMode={scoringMode}
                      onChange={(mode) => {
                        setScoringMode(mode)
                        localStorage.setItem('scoringMode', mode)
                      }}
                      className={styles.scoringModeToggle}
                    />
                    <PerspectiveSelector
                      selectedPerspective={selectedPerspective}
                      onChange={setSelectedPerspective}
                      className={styles.scoringModeToggle}
                    />
                  </>
                )}
                {displayMode === 'trend' && (
                  <>
                    <ReturnTypeToggle
                      returnType={returnType}
                      onChange={setReturnType}
                    />
                    <PeriodSelector
                      selectedPeriods={selectedPeriods}
                      onChange={setSelectedPeriods}
                    />
                  </>
                )}
              </>
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
            isHolding={isHolding}
            perspective={selectedPerspective}
          />
        ) : (
          <ETFTableView
            items={items}
            performance={performance}
            scores={scores}
            displayMode={displayMode}
            selectedPeriods={selectedPeriods}
            selectedPerspective={selectedPerspective}
            returnType={returnType}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
            isHolding={isHolding}
            sortField={currentSort}
            sortOrder={currentOrder}
            onSortChange={handleSortChange}
          />
        )}
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </section>

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
