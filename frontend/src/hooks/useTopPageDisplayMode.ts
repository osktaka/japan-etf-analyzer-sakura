import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { SortField, SortOrder, PerformancePeriod } from '../api'
import type {
  ViewMode,
  ReturnType,
  DisplayMode,
  PerspectiveKey,
  ScoringMode,
} from '../components/search'
import { useTopPageStorage } from './useTopPageStorage'

// 切り口からソートフィールドへのマッピング（共通定義）
export const PERSPECTIVE_TO_SORT_FIELD: Record<PerspectiveKey, SortField> = {
  balance: 'score_balance',
  dividend: 'score_dividend',
  'low-cost': 'score_low_cost',
  stability: 'score_stability',
  volume: 'score_volume',
  growth: 'score_growth',
}

export interface DisplayModeState {
  viewMode: ViewMode
  displayMode: DisplayMode
  scoringMode: ScoringMode
  selectedPerspective: PerspectiveKey
  selectedPeriods: PerformancePeriod[]
  returnType: ReturnType
}

export interface DisplayModeActions {
  setViewMode: (mode: ViewMode) => void
  setDisplayMode: (mode: DisplayMode) => void
  setScoringMode: (mode: ScoringMode) => void
  setSelectedPerspective: (perspective: PerspectiveKey) => void
  setSelectedPeriods: (periods: PerformancePeriod[]) => void
  setReturnType: (returnType: ReturnType) => void
  handleViewModeChange: (mode: ViewMode) => void
  handleScoringModeChange: (mode: ScoringMode) => void
}

export interface SearchOverrides {
  sort?: SortField
  order?: SortOrder
  page?: number
  keyword?: string
}

export interface UseTopPageDisplayModeOptions {
  /** 現在のソート状態を取得する関数（動的に最新値を参照） */
  getCurrentSort: () => SortField
  currentOrder: SortOrder
  /** ソート更新時のコールバック */
  onSortUpdate: (sort: SortField, order: SortOrder) => void
  /** 検索実行コールバック */
  onSearchRequest: (overrides?: SearchOverrides) => void
}

export interface UseTopPageDisplayModeResult extends DisplayModeState, DisplayModeActions {
  /** 初期viewModeを取得（ソート初期化用） */
  getInitialViewMode: () => ViewMode
  /** viewMode変更時のソート保存・復元用ref */
  isInitialMount: React.MutableRefObject<boolean>
  /** displayModeの前回値ref */
  prevDisplayModeRef: React.MutableRefObject<DisplayMode>
  /** viewModeの前回値ref */
  prevViewModeRef: React.MutableRefObject<ViewMode>
}

/**
 * TopPageの表示モード関連状態を管理するカスタムフック
 *
 * 管理対象:
 * - viewMode: カード/テーブル表示切替
 * - displayMode: スコア/傾向表示切替（テーブル時のみ）
 * - scoringMode: 全指標/部分評価モード
 * - selectedPerspective: 選択中の切り口
 * - selectedPeriods: 表示対象の期間
 * - returnType: 株価騰落率/回帰分析
 *
 * 機能:
 * - URLパラメータ/localStorageからの復元
 * - モード変更時のソート状態保存/復元
 * - モード変更時の検索再実行トリガー
 */
export function useTopPageDisplayMode(
  options: UseTopPageDisplayModeOptions
): UseTopPageDisplayModeResult {
  const { getCurrentSort, currentOrder, onSortUpdate, onSearchRequest } = options
  const [searchParams, setSearchParams] = useSearchParams()
  const storage = useTopPageStorage()

  // 表示モードの初期値を取得（ソート初期化で参照するため）
  const getInitialViewMode = useCallback((): ViewMode => {
    const urlView = searchParams.get('view') as ViewMode
    if (urlView) return urlView
    const storedView = storage.getStoredViewMode()
    return storedView || 'card'
  }, [searchParams, storage])

  // 表示モード（URL優先 → localStorage → デフォルト）
  const [viewMode, setViewMode] = useState<ViewMode>(getInitialViewMode)
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

  // refs for mode change detection
  const isInitialMount = useRef(true)
  const isScoringModeInitialMount = useRef(true)
  const isReturnTypeInitialMount = useRef(true)
  const isPerspectiveInitialMount = useRef(true)
  const prevDisplayModeRef = useRef<DisplayMode>(displayMode)
  const prevViewModeRef = useRef<ViewMode>(viewMode)

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
    const prevSort = getCurrentSort()
    storage.saveSortState(
      prevViewModeRef.current,
      displayMode,
      prevSort,
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

    // カード形式に切り替えた時は displayMode を 'score' にリセット
    if (viewMode === 'card') {
      setDisplayMode('score')
    }

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

    // ソート更新をコールバックで通知
    onSortUpdate(newSort, newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== prevSort || newOrder !== currentOrder) {
      onSearchRequest({ sort: newSort, order: newOrder })
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
    const sortField = getCurrentSort()
    const isPerformanceSort = [
      'return_1m',
      'return_3m',
      'return_6m',
      'return_1y',
      'return_3y',
      'return_5y',
      'return_10y',
      'return_20y',
    ].includes(sortField)

    if (isPerformanceSort) {
      onSearchRequest()
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
    const sortField = getCurrentSort()
    const isScoreSort = sortField.startsWith('score_')

    if (isScoreSort) {
      onSearchRequest()
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
    const sortField = getCurrentSort()
    const isScoreSort =
      sortField === 'evaluation_score' || sortField.startsWith('score_')

    if (isScoreSort) {
      const newSort = PERSPECTIVE_TO_SORT_FIELD[selectedPerspective]
      onSortUpdate(newSort, currentOrder)
      onSearchRequest({ sort: newSort, order: currentOrder })
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
    const prevSort = getCurrentSort()
    storage.saveSortState(
      viewMode,
      prevDisplayModeRef.current,
      prevSort,
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

    // ソート更新をコールバックで通知
    onSortUpdate(newSort, newOrder)

    // ソート状態が変わった場合は検索を実行
    if (newSort !== prevSort || newOrder !== currentOrder) {
      onSearchRequest({ sort: newSort, order: newOrder })
    }
    // displayMode変更時のみ実行（他の依存は意図的に除外）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayMode])

  // viewMode変更時のハンドラ（URL更新も含む）
  const handleViewModeChange = useCallback(
    (mode: ViewMode) => {
      setViewMode(mode)
      setSearchParams(
        (prev) => {
          const newParams = new URLSearchParams(prev)
          if (mode === 'card') {
            newParams.delete('view')
          } else {
            newParams.set('view', mode)
          }
          return newParams
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  // scoringMode変更時のハンドラ（localStorage保存も含む）
  const handleScoringModeChange = useCallback((mode: ScoringMode) => {
    setScoringMode(mode)
    localStorage.setItem('scoringMode', mode)
  }, [])

  return {
    // State
    viewMode,
    displayMode,
    scoringMode,
    selectedPerspective,
    selectedPeriods,
    returnType,
    // Actions
    setViewMode,
    setDisplayMode,
    setScoringMode,
    setSelectedPerspective,
    setSelectedPeriods,
    setReturnType,
    handleViewModeChange,
    handleScoringModeChange,
    // Utilities
    getInitialViewMode,
    isInitialMount,
    prevDisplayModeRef,
    prevViewModeRef,
  }
}
