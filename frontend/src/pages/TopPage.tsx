/** Top page component */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  useETFSearch,
  useCompareList,
  useFavorites,
  useAuth,
  usePortfolio,
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
} from '../components/search'
import type { ViewMode, ReturnType, DisplayMode } from '../components/search'
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
import { MAX_COMPARE_ITEMS } from '../utils'
import styles from './TopPage.module.css'

const PAGE_SIZE = 50
const PERIODS_STORAGE_KEY = 'etf-table-view-periods'
const RETURN_TYPE_STORAGE_KEY = 'etf-return-type'
const VIEW_MODE_STORAGE_KEY = 'etf-view-mode'
const SCORE_SORT_STORAGE_KEY = 'etf-score-sort-state'
const TREND_SORT_STORAGE_KEY = 'etf-trend-sort-state'
const CARD_SORT_STORAGE_KEY = 'etf-card-sort-state'
const DISPLAY_MODE_STORAGE_KEY = 'etf-table-display-mode'

// ローカルストレージから表示期間を復元
const getStoredPeriods = (): PerformancePeriod[] => {
  try {
    const stored = localStorage.getItem(PERIODS_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch {
    // パースエラー時はデフォルト値を返す
  }
  return ['6m', '1y', '3y']
}

// ローカルストレージから上昇率タイプを復元
const getStoredReturnType = (): ReturnType => {
  try {
    const stored = localStorage.getItem(RETURN_TYPE_STORAGE_KEY)
    if (stored === 'price' || stored === 'regression') {
      return stored
    }
  } catch {
    // エラー時はデフォルト値を返す
  }
  return 'price'
}

// ローカルストレージから表示モードを復元
const getStoredViewMode = (): ViewMode | null => {
  try {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    if (stored === 'card' || stored === 'table') {
      return stored
    }
  } catch {
    // エラー時はnullを返す
  }
  return null
}

// ローカルストレージから銘柄スコア表示用のソート状態を復元
const getStoredScoreSort = (): { sort: SortField; order: SortOrder } => {
  try {
    const stored = localStorage.getItem(SCORE_SORT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (
        parsed &&
        typeof parsed.sort === 'string' &&
        typeof parsed.order === 'string'
      ) {
        return parsed
      }
    }
  } catch {
    // パースエラー時はデフォルト値を返す
  }
  return { sort: 'score_balance', order: 'desc' }
}

// ローカルストレージから株価傾向表示用のソート状態を復元
const getStoredTrendSort = (): { sort: SortField; order: SortOrder } => {
  try {
    const stored = localStorage.getItem(TREND_SORT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (
        parsed &&
        typeof parsed.sort === 'string' &&
        typeof parsed.order === 'string'
      ) {
        return parsed
      }
    }
  } catch {
    // パースエラー時はデフォルト値を返す
  }
  return { sort: 'return_1y', order: 'desc' }
}

// ローカルストレージからカード形式用のソート状態を復元
const getStoredCardSort = (): { sort: SortField; order: SortOrder } => {
  try {
    const stored = localStorage.getItem(CARD_SORT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (
        parsed &&
        typeof parsed.sort === 'string' &&
        typeof parsed.order === 'string'
      ) {
        return parsed
      }
    }
  } catch {
    // パースエラー時はデフォルト値を返す
  }
  return { sort: 'return_1y', order: 'desc' }
}

// ローカルストレージから表示モードを復元
const getStoredDisplayMode = (): DisplayMode => {
  try {
    const stored = localStorage.getItem(DISPLAY_MODE_STORAGE_KEY)
    if (stored === 'score' || stored === 'trend') {
      return stored
    }
  } catch {
    // エラー時はデフォルト値を返す
  }
  return 'trend'
}

// ソート状態をローカルストレージに保存するヘルパー関数
const saveSortState = (
  viewMode: ViewMode,
  displayMode: DisplayMode,
  sort: SortField,
  order: SortOrder
): void => {
  if (viewMode === 'card') {
    localStorage.setItem(
      CARD_SORT_STORAGE_KEY,
      JSON.stringify({ sort, order })
    )
  } else if (viewMode === 'table') {
    const storageKey =
      displayMode === 'score' ? SCORE_SORT_STORAGE_KEY : TREND_SORT_STORAGE_KEY
    localStorage.setItem(storageKey, JSON.stringify({ sort, order }))
  }
}

export function TopPage() {
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

  // 表示モードの初期値を取得（ソート初期化で参照するため）
  const getInitialViewMode = (): ViewMode => {
    const urlView = searchParams.get('view') as ViewMode
    if (urlView) return urlView
    const storedView = getStoredViewMode()
    return storedView || 'card'
  }

  // 表示モード（URL優先 → localStorage → デフォルト）
  const [viewMode, setViewMode] = useState<ViewMode>(getInitialViewMode)
  const [performance, setPerformance] = useState<BatchPerformanceData>({})
  const [scores, setScores] = useState<BatchScoreData>({})
  const [selectedPeriods, setSelectedPeriods] =
    useState<PerformancePeriod[]>(getStoredPeriods)
  const [returnType, setReturnType] = useState<ReturnType>(getStoredReturnType)
  const [displayMode, setDisplayMode] =
    useState<DisplayMode>(getStoredDisplayMode)
  const [scoringMode, setScoringMode] = useState<'full' | 'partial'>(() => {
    const saved = localStorage.getItem('scoringMode')
    return (saved === 'partial' ? 'partial' : 'full') as 'full' | 'partial'
  })

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
    const initialDisplayMode = getStoredDisplayMode()
    // カード形式の場合
    if (initialViewMode === 'card') {
      const storedSort = getStoredCardSort()
      return storedSort.sort
    }
    // 表形式かつスコア表示の場合
    if (initialDisplayMode === 'score') {
      const storedSort = getStoredScoreSort()
      return storedSort.sort
    }
    // 表形式かつ傾向表示の場合
    const storedSort = getStoredTrendSort()
    return storedSort.sort
  })
  const [currentOrder, setCurrentOrder] = useState<SortOrder>(() => {
    const urlOrder = searchParams.get('order') as SortOrder
    if (urlOrder) return urlOrder
    const initialViewMode = getInitialViewMode()
    const initialDisplayMode = getStoredDisplayMode()
    // カード形式の場合
    if (initialViewMode === 'card') {
      const storedSort = getStoredCardSort()
      return storedSort.order
    }
    // 表形式かつスコア表示の場合
    if (initialDisplayMode === 'score') {
      const storedSort = getStoredScoreSort()
      return storedSort.order
    }
    // 表形式かつ傾向表示の場合
    const storedSort = getStoredTrendSort()
    return storedSort.order
  })
  const [currentPage, setCurrentPage] = useState(
    Number(searchParams.get('page')) || 1
  )

  const etfListRef = useRef<HTMLElement>(null)
  const isInitialMount = useRef(true)
  const isScoringModeInitialMount = useRef(true)
  const isReturnTypeInitialMount = useRef(true)
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
    localStorage.setItem(PERIODS_STORAGE_KEY, JSON.stringify(selectedPeriods))
  }, [selectedPeriods])

  // 上昇率タイプをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(RETURN_TYPE_STORAGE_KEY, returnType)
  }, [returnType])

  // 表示モードをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode)
  }, [viewMode])

  // viewMode変更時にソート状態を保存・復元
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isInitialMount.current) {
      return
    }

    // 前回のviewModeのソート状態を保存（prevViewModeRef.currentは前のviewModeを指している）
    saveSortState(prevViewModeRef.current, displayMode, currentSort, currentOrder)

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
      storedSort = getStoredCardSort()
    } else if (displayMode === 'score') {
      storedSort = getStoredScoreSort()
    } else {
      storedSort = getStoredTrendSort()
    }

    const newSort = storedSort.sort
    const newOrder = storedSort.order

    setCurrentSort(newSort)
    setCurrentOrder(newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== currentSort || newOrder !== currentOrder) {
      const searchParams: SearchParams = {
        ...currentFilters,
        keyword: currentKeyword || undefined,
        sort: newSort,
        order: newOrder,
        return_type: returnType,
        scoring_mode: scoringMode,
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }

      if (favoritesOnly) {
        searchParams.favorite_codes = Array.from(favoriteCodes)
      }

      if (holdingsOnly) {
        searchParams.holding_codes = Array.from(holdingCodes)
      }

      if (compareOnly) {
        searchParams.favorite_codes = compareCodes
      }

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
      const searchParams: SearchParams = {
        ...currentFilters,
        keyword: currentKeyword || undefined,
        sort: currentSort,
        order: currentOrder,
        return_type: returnType,
        scoring_mode: scoringMode,
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }

      if (favoritesOnly) {
        searchParams.favorite_codes = Array.from(favoriteCodes)
      }

      if (holdingsOnly) {
        searchParams.holding_codes = Array.from(holdingCodes)
      }

      if (compareOnly) {
        searchParams.favorite_codes = compareCodes
      }

      search(searchParams)
    }
    // returnType変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [returnType])

  // 表示モードをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(DISPLAY_MODE_STORAGE_KEY, displayMode)
  }, [displayMode])

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
      const searchParams: SearchParams = {
        ...currentFilters,
        keyword: currentKeyword || undefined,
        sort: currentSort,
        order: currentOrder,
        return_type: returnType,
        scoring_mode: scoringMode,
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }

      if (favoritesOnly) {
        searchParams.favorite_codes = Array.from(favoriteCodes)
      }

      if (holdingsOnly) {
        searchParams.holding_codes = Array.from(holdingCodes)
      }

      if (compareOnly) {
        searchParams.favorite_codes = compareCodes
      }

      search(searchParams)
    }
    // scoringMode変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoringMode])

  // displayMode変更時にソート状態を保存・復元
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isInitialMount.current) {
      return
    }

    // 前回のモードのソート状態を保存（prevDisplayModeRef.currentは前のdisplayModeを指している）
    saveSortState(viewMode, prevDisplayModeRef.current, currentSort, currentOrder)

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
      displayMode === 'score' ? getStoredScoreSort() : getStoredTrendSort()

    const newSort = storedSort.sort
    const newOrder = storedSort.order

    setCurrentSort(newSort)
    setCurrentOrder(newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== currentSort || newOrder !== currentOrder) {
      const searchParams: SearchParams = {
        ...currentFilters,
        keyword: currentKeyword || undefined,
        sort: newSort,
        order: newOrder,
        return_type: returnType,
        scoring_mode: scoringMode,
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }

      if (favoritesOnly) {
        searchParams.favorite_codes = Array.from(favoriteCodes)
      }

      if (holdingsOnly) {
        searchParams.holding_codes = Array.from(holdingCodes)
      }

      if (compareOnly) {
        searchParams.favorite_codes = compareCodes
      }

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
    const defaultSort = initialViewMode === 'table' ? 'return_1y' : 'code'
    const defaultOrder = initialViewMode === 'table' ? 'desc' : 'asc'
    const sort = (searchParams.get('sort') as SortField) || defaultSort
    const order = (searchParams.get('order') as SortOrder) || defaultOrder
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

    const searchParams: SearchParams = {
      ...currentFilters,
      keyword: trimmed || undefined,
      sort: currentSort,
      order: currentOrder,
      return_type: returnType,
      scoring_mode: scoringMode,
      limit: PAGE_SIZE,
      offset: 0,
    }

    if (favoritesOnly) {
      // 0件でも空配列を渡して「該当なし」を表示
      searchParams.favorite_codes = Array.from(favoriteCodes)
    }

    if (holdingsOnly) {
      // 0件でも空配列を渡して「該当なし」を表示
      searchParams.holding_codes = Array.from(holdingCodes)
    }

    if (compareOnly) {
      // 比較リストで絞り込み
      searchParams.favorite_codes = compareCodes
    }

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

      const searchParams: SearchParams = {
        ...filters,
        keyword: currentKeyword || undefined,
        sort: currentSort,
        order: currentOrder,
        return_type: returnType,
        scoring_mode: scoringMode,
        limit: PAGE_SIZE,
        offset: 0,
      }

      if (favoritesOnly) {
        searchParams.favorite_codes = Array.from(favoriteCodes)
      }

      if (holdingsOnly) {
        searchParams.holding_codes = Array.from(holdingCodes)
      }

      if (compareOnly) {
        searchParams.favorite_codes = compareCodes
      }

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
    saveSortState(viewMode, displayMode, sort, order)

    updateURL({
      sort,
      order,
      page: '1',
    })

    const searchParams: SearchParams = {
      ...currentFilters,
      keyword: currentKeyword || undefined,
      sort,
      order,
      return_type: returnType,
      scoring_mode: scoringMode,
      limit: PAGE_SIZE,
      offset: 0,
    }

    if (favoritesOnly) {
      searchParams.favorite_codes = Array.from(favoriteCodes)
    }

    if (holdingsOnly) {
      searchParams.holding_codes = Array.from(holdingCodes)
    }

    search(searchParams)
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)

    updateURL({
      page: page.toString(),
    })

    const searchParams: SearchParams = {
      ...currentFilters,
      keyword: currentKeyword || undefined,
      sort: currentSort,
      order: currentOrder,
      return_type: returnType,
      scoring_mode: scoringMode,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    }

    if (favoritesOnly) {
      searchParams.favorite_codes = Array.from(favoriteCodes)
    }

    if (holdingsOnly) {
      searchParams.holding_codes = Array.from(holdingCodes)
    }

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

    const params: SearchParams = {
      ...currentFilters,
      keyword: currentKeyword || undefined,
      sort: currentSort,
      order: currentOrder,
      return_type: returnType,
      scoring_mode: scoringMode,
      limit: PAGE_SIZE,
      offset: 0,
    }

    if (favoritesOnly) {
      params.favorite_codes = Array.from(favoriteCodes)
    }

    if (holdingsOnly) {
      params.holding_codes = Array.from(holdingCodes)
    }

    if (compareOnly) {
      params.favorite_codes = compareCodes
    }

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
                  <div className={styles.scoringModeToggle}>
                    <button
                      className={`${styles.toggleButton} ${scoringMode === 'full' ? styles.active : ''}`}
                      onClick={() => {
                        setScoringMode('full')
                        localStorage.setItem('scoringMode', 'full')
                      }}
                    >
                      総合評価
                    </button>
                    <button
                      className={`${styles.toggleButton} ${scoringMode === 'partial' ? styles.active : ''}`}
                      onClick={() => {
                        setScoringMode('partial')
                        localStorage.setItem('scoringMode', 'partial')
                      }}
                    >
                      軸別評価
                    </button>
                  </div>
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
          />
        ) : (
          <ETFTableView
            items={items}
            performance={performance}
            scores={scores}
            displayMode={displayMode}
            selectedPeriods={selectedPeriods}
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
