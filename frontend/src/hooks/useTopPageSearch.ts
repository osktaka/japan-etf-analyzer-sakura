/** TopPage search state management hook */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SearchParams, SortField, SortOrder, CustomWeights } from '../api'
import { useETFSearch } from './useETFSearch'
import { useTopPageStorage } from './useTopPageStorage'
import { PERSPECTIVE_TO_SORT_FIELD } from './useTopPageDisplayMode'
import { buildSearchParams } from '../utils'

export const PAGE_SIZE = 50

export interface UseTopPageSearchOptions {
  returnType: 'price' | 'regression'
  scoringMode: 'full' | 'partial'
  selectedPerspective: string
  customWeights: CustomWeights | null
  favoriteCodes: Set<string>
  holdingCodes: Set<string>
  compareCodes: string[]
  getInitialViewMode: () => 'card' | 'table'
  viewMode: 'card' | 'table'
  displayMode: 'score' | 'trend'
}

export interface UseTopPageSearchResult {
  // State
  currentKeyword: string
  currentFilters: SearchParams
  currentSort: SortField
  currentOrder: SortOrder
  currentPage: number
  hasSearched: boolean
  favoritesOnly: boolean
  holdingsOnly: boolean
  compareOnly: boolean
  totalPages: number

  // Setters
  setCurrentKeyword: (keyword: string) => void
  setCurrentFilters: (filters: SearchParams) => void
  setCurrentSort: (sort: SortField) => void
  setCurrentOrder: (order: SortOrder) => void
  setFavoritesOnly: (value: boolean) => void
  setHoldingsOnly: (value: boolean) => void
  setCompareOnly: (value: boolean) => void

  // Search data
  items: ReturnType<typeof useETFSearch>['items']
  total: ReturnType<typeof useETFSearch>['total']
  isLoading: ReturnType<typeof useETFSearch>['isLoading']
  error: ReturnType<typeof useETFSearch>['error']

  // Handlers
  handleSearch: (keyword: string) => void
  handleFilter: (filters: SearchParams) => void
  handleSortChange: (sort: SortField, order: SortOrder) => void
  handlePageChange: (page: number) => void

  // Utilities
  executeSearch: (overrides?: SearchOverrides) => void
  searchRequestRef: React.MutableRefObject<() => void>
  etfListRef: React.RefObject<HTMLElement>
  getInitialFilters: () => SearchParams
  updateURL: (params: URLParams) => void
}

interface SearchOverrides {
  sort?: SortField
  order?: SortOrder
  page?: number
  keyword?: string
  filters?: SearchParams
  perspective?: string
}

interface URLParams {
  tab?: string
  q?: string
  sort?: string
  order?: string
  page?: string
  category?: string
  tags?: string
  min_dividend?: string
  max_expense?: string
  view?: string
}

export function useTopPageSearch(
  options: UseTopPageSearchOptions
): UseTopPageSearchResult {
  const {
    returnType,
    scoringMode,
    selectedPerspective,
    customWeights,
    favoriteCodes,
    holdingCodes,
    compareCodes,
    getInitialViewMode,
    viewMode,
    displayMode,
  } = options

  const [searchParams, setSearchParams] = useSearchParams()
  const storage = useTopPageStorage()

  // URLパラメータから初期フィルターを復元
  const getInitialFilters = useCallback((): SearchParams => {
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
  }, [searchParams])

  // 初期ソート状態を取得
  const getInitialSort = useCallback((): {
    sort: SortField
    order: SortOrder
  } => {
    const urlSort = searchParams.get('sort') as SortField
    const urlOrder = searchParams.get('order') as SortOrder
    if (urlSort) return { sort: urlSort, order: urlOrder || 'desc' }

    const urlView = searchParams.get('view')
    const storedView = storage.getStoredViewMode()
    const initialViewMode = urlView || storedView || 'card'
    const initialDisplayMode = storage.getStoredDisplayMode()

    // カード形式の場合
    if (initialViewMode === 'card') {
      const storedSort = storage.getStoredCardSort()
      const initialPerspective = storage.getStoredPerspective()
      // score_*ソート時は選択中の切り口を反映
      if (storedSort.sort.startsWith('score_')) {
        return {
          sort: PERSPECTIVE_TO_SORT_FIELD[initialPerspective],
          order: storedSort.order,
        }
      }
      return storedSort
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
        return {
          sort: PERSPECTIVE_TO_SORT_FIELD[initialPerspective],
          order: storedSort.order,
        }
      }
      return storedSort
    }
    // 表形式かつ傾向表示の場合
    return storage.getStoredTrendSort()
  }, [searchParams, storage])

  // State
  const [hasSearched, setHasSearched] = useState(false)
  const [currentKeyword, setCurrentKeyword] = useState(
    searchParams.get('q') || ''
  )
  const [currentFilters, setCurrentFilters] =
    useState<SearchParams>(getInitialFilters())

  const initialSort = useMemo(() => getInitialSort(), [getInitialSort])
  const [currentSort, setCurrentSort] = useState<SortField>(initialSort.sort)
  const [currentOrder, setCurrentOrder] = useState<SortOrder>(initialSort.order)
  const [currentPage, setCurrentPage] = useState(
    Number(searchParams.get('page')) || 1
  )

  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [holdingsOnly, setHoldingsOnly] = useState(false)
  const [compareOnly, setCompareOnly] = useState(false)

  const etfListRef = useRef<HTMLElement>(null)
  const searchRequestRef = useRef<() => void>(() => {})

  // 独立した初回マウント判定フラグ（favoritesOnly/holdingsOnly/compareOnly用）
  const isFilterInitialMount = useRef(true)

  const { items, total, isLoading, error, search } = useETFSearch()

  // URLパラメータ更新ヘルパー
  const updateURL = useCallback(
    (params: Partial<URLParams>) => {
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

  // 検索実行関数
  const executeSearch = useCallback(
    (overrides?: SearchOverrides) => {
      const params = buildSearchParams({
        currentFilters: overrides?.filters ?? currentFilters,
        currentKeyword: overrides?.keyword ?? currentKeyword,
        currentSort: overrides?.sort ?? currentSort,
        currentOrder: overrides?.order ?? currentOrder,
        currentPage: overrides?.page ?? currentPage,
        returnType,
        scoringMode,
        perspective: overrides?.perspective ?? selectedPerspective,
        customWeights,
        pageSize: PAGE_SIZE,
        favoritesOnly,
        holdingsOnly,
        compareOnly,
        favoriteCodes,
        holdingCodes,
        compareCodes,
      })
      search(params)
    },
    [
      currentFilters,
      currentKeyword,
      currentSort,
      currentOrder,
      currentPage,
      returnType,
      scoringMode,
      selectedPerspective,
      customWeights,
      favoritesOnly,
      holdingsOnly,
      compareOnly,
      favoriteCodes,
      holdingCodes,
      compareCodes,
      search,
    ]
  )

  // searchRequestRefを更新
  useEffect(() => {
    searchRequestRef.current = () => executeSearch()
  }, [executeSearch])

  // 初回マウント時の検索実行
  useEffect(() => {
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

    const initialParams: SearchParams = {
      ...filters,
      keyword,
      sort,
      order,
      return_type: returnType,
      scoring_mode: scoringMode,
      perspective: selectedPerspective,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    }

    // Add custom_weights if sorting by custom score
    if (sort === 'score_custom' && customWeights) {
      initialParams.custom_weights = JSON.stringify(customWeights)
    }

    search(initialParams)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // 初回のみ実行

  // お気に入り/保有中/比較フィルター状態が変わったときに検索を実行
  useEffect(() => {
    // 初回マウント時はスキップ（初回検索は別のuseEffectで実行済み）
    if (isFilterInitialMount.current) {
      isFilterInitialMount.current = false
      return
    }

    setCurrentPage(1)
    executeSearch({ page: 1 })
    // favoritesOnly/holdingsOnly/compareOnly変更時のみ発動
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [favoritesOnly, holdingsOnly, compareOnly])

  // Handlers
  const handleSearch = useCallback(
    (keyword: string) => {
      const trimmed = keyword.trim()
      setCurrentKeyword(trimmed)
      setHasSearched(!!trimmed)
      setCurrentPage(1)

      updateURL({
        q: trimmed,
        page: '1',
      })

      executeSearch({ keyword: trimmed, page: 1 })

      etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
    },
    [updateURL, executeSearch]
  )

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

      executeSearch({ filters, page: 1 })
    },
    [currentKeyword, updateURL, executeSearch]
  )

  const handleSortChange = useCallback(
    (sort: SortField, order: SortOrder) => {
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

      executeSearch({ sort, order, page: 1 })
    },
    [storage, viewMode, displayMode, updateURL, executeSearch]
  )

  const handlePageChange = useCallback(
    (page: number) => {
      setCurrentPage(page)

      updateURL({
        page: page.toString(),
      })

      executeSearch({ page })
      etfListRef.current?.scrollIntoView({ behavior: 'smooth' })
    },
    [updateURL, executeSearch]
  )

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return {
    // State
    currentKeyword,
    currentFilters,
    currentSort,
    currentOrder,
    currentPage,
    hasSearched,
    favoritesOnly,
    holdingsOnly,
    compareOnly,
    totalPages,

    // Setters
    setCurrentKeyword,
    setCurrentFilters,
    setCurrentSort,
    setCurrentOrder,
    setFavoritesOnly,
    setHoldingsOnly,
    setCompareOnly,

    // Search data
    items,
    total,
    isLoading,
    error,

    // Handlers
    handleSearch,
    handleFilter,
    handleSortChange,
    handlePageChange,

    // Utilities
    executeSearch,
    searchRequestRef,
    etfListRef,
    getInitialFilters,
    updateURL,
  }
}
