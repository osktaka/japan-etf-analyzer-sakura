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
  const isScoringModeInitialMount = useRef(true)
  const isReturnTypeInitialMount = useRef(true)
  const isPerspectiveInitialMount = useRef(true)
  const isPeriodsInitialMount = useRef(true)
  const isDisplayModeInitialMount = useRef(true)
  const isViewModeInitialMount = useRef(true)
  const prevDisplayModeRef = useRef<DisplayMode>(displayMode)
  const prevViewModeRef = useRef<ViewMode>(viewMode)

  // 表示期間をローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(
      storage.keys.PERIODS_STORAGE_KEY,
      JSON.stringify(selectedPeriods)
    )
  }, [selectedPeriods, storage.keys.PERIODS_STORAGE_KEY])

  // selectedPeriods変更時に一覧を再取得
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isPeriodsInitialMount.current) {
      isPeriodsInitialMount.current = false
    } else {
      onSearchRequest()
    }
    // selectedPeriods変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPeriods])

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
    if (isViewModeInitialMount.current) {
      isViewModeInitialMount.current = false
    } else {
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
      // （既に'score'の場合は状態変更を避けてuseEffect連鎖を防止）
      if (viewMode === 'card' && displayMode !== 'score') {
        setDisplayMode('score')
      }

      // 新しいソート状態を決定
      let newSort: SortField
      let newOrder: SortOrder

      if (viewMode === 'card') {
        // カード表示時は現在の切り口に対応するスコアで降順ソート
        newSort = PERSPECTIVE_TO_SORT_FIELD[selectedPerspective]
        newOrder = 'desc'
      } else {
        // テーブル表示時はlocalStorageから復元
        const storedSort =
          displayMode === 'score'
            ? storage.getStoredScoreSort()
            : storage.getStoredTrendSort()
        newSort = storedSort.sort
        newOrder = storedSort.order
      }

      // ソート更新をコールバックで通知
      onSortUpdate(newSort, newOrder)

      // 検索を実行
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
    } else {
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
    }
    // returnType変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [returnType])

  // 表示モードをローカルストレージに保存
  useEffect(() => {
    localStorage.setItem(storage.keys.DISPLAY_MODE_STORAGE_KEY, displayMode)
  }, [displayMode, storage.keys.DISPLAY_MODE_STORAGE_KEY])

  // scoringMode変更時に一覧を再取得
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isScoringModeInitialMount.current) {
      isScoringModeInitialMount.current = false
    } else {
      onSearchRequest()
    }
    // scoringMode変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoringMode])

  // selectedPerspective変更時に対応する切り口でソート（カード表示時またはテーブル＋スコア表示時に連動）
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isPerspectiveInitialMount.current) {
      isPerspectiveInitialMount.current = false
    } else {
      // カード表示時、またはテーブル＋スコア表示時は対応するperspectiveソートに変更してAPI再取得
      if (viewMode === 'card' || displayMode === 'score') {
        const newSort = PERSPECTIVE_TO_SORT_FIELD[selectedPerspective]
        onSortUpdate(newSort, 'desc')
        onSearchRequest({ sort: newSort, order: 'desc' })
      }
    }
    // selectedPerspective変更時のみ実行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPerspective])

  // displayMode変更時にソート状態を保存・復元
  useEffect(() => {
    // 初回マウント時はスキップ
    if (isDisplayModeInitialMount.current) {
      isDisplayModeInitialMount.current = false
    } else {
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

      // 検索を実行
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

  // コンポーネントのアンマウント時に初期マウントフラグをリセット
  useEffect(() => {
    return () => {
      isPerspectiveInitialMount.current = true
      isViewModeInitialMount.current = true
      isDisplayModeInitialMount.current = true
      isScoringModeInitialMount.current = true
      isPeriodsInitialMount.current = true
      isReturnTypeInitialMount.current = true
    }
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
    prevDisplayModeRef,
    prevViewModeRef,
  }
}
