import type { SortField, SortOrder, PerformancePeriod } from '../api'
import type {
  ViewMode,
  ReturnType,
  DisplayMode,
  PerspectiveKey,
} from '../components/search'

// ローカルストレージキー定数
const PERIODS_STORAGE_KEY = 'etf-table-view-periods'
const RETURN_TYPE_STORAGE_KEY = 'etf-return-type'
const VIEW_MODE_STORAGE_KEY = 'etf-view-mode'
const SCORE_SORT_STORAGE_KEY = 'etf-score-sort-state'
const TREND_SORT_STORAGE_KEY = 'etf-trend-sort-state'
const CARD_SORT_STORAGE_KEY = 'etf-card-sort-state'
const DISPLAY_MODE_STORAGE_KEY = 'etf-table-display-mode'
const PERSPECTIVE_STORAGE_KEY = 'etf-perspective'

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

// ソート状態復元の共通ヘルパー
const getStoredSort = (
  key: string,
  defaultSort: SortField,
  defaultOrder: SortOrder
): { sort: SortField; order: SortOrder } => {
  try {
    const stored = localStorage.getItem(key)
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
  return { sort: defaultSort, order: defaultOrder }
}

// ローカルストレージから銘柄スコア表示用のソート状態を復元
const getStoredScoreSort = (): { sort: SortField; order: SortOrder } =>
  getStoredSort(SCORE_SORT_STORAGE_KEY, 'score_balance', 'desc')

// ローカルストレージから株価傾向表示用のソート状態を復元
const getStoredTrendSort = (): { sort: SortField; order: SortOrder } =>
  getStoredSort(TREND_SORT_STORAGE_KEY, 'return_1y', 'desc')

// ローカルストレージからカード形式用のソート状態を復元
const getStoredCardSort = (): { sort: SortField; order: SortOrder } =>
  getStoredSort(CARD_SORT_STORAGE_KEY, 'return_1y', 'desc')

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

// ローカルストレージから切り口を復元
const getStoredPerspective = (): PerspectiveKey => {
  try {
    const stored = localStorage.getItem(PERSPECTIVE_STORAGE_KEY)
    const validPerspectives: PerspectiveKey[] = [
      'balance',
      'dividend',
      'low-cost',
      'stability',
      'volume',
      'growth',
    ]
    if (stored && validPerspectives.includes(stored as PerspectiveKey)) {
      return stored as PerspectiveKey
    }
  } catch {
    // エラー時はデフォルト値を返す
  }
  return 'balance'
}

// ソート状態をローカルストレージに保存するヘルパー関数
const saveSortState = (
  viewMode: ViewMode,
  displayMode: DisplayMode,
  sort: SortField,
  order: SortOrder
): void => {
  if (viewMode === 'card') {
    localStorage.setItem(CARD_SORT_STORAGE_KEY, JSON.stringify({ sort, order }))
  } else if (viewMode === 'table') {
    const storageKey =
      displayMode === 'score' ? SCORE_SORT_STORAGE_KEY : TREND_SORT_STORAGE_KEY
    localStorage.setItem(storageKey, JSON.stringify({ sort, order }))
  }
}

/**
 * TopPageのローカルストレージ操作を管理するカスタムフック
 *
 * 8つのストレージ関数を提供:
 * - Get関数: 表示期間、上昇率タイプ、表示モード、ソート状態、切り口を復元
 * - Save関数: ソート状態を保存
 * - ストレージキー: 直接localStorage.setItemする際に使用
 */
export function useTopPageStorage() {
  return {
    // Get関数
    getStoredPeriods,
    getStoredReturnType,
    getStoredViewMode,
    getStoredScoreSort,
    getStoredTrendSort,
    getStoredCardSort,
    getStoredDisplayMode,
    getStoredPerspective,
    // Save関数
    saveSortState,
    // ストレージキー（useEffect等での直接保存用）
    keys: {
      PERIODS_STORAGE_KEY,
      RETURN_TYPE_STORAGE_KEY,
      VIEW_MODE_STORAGE_KEY,
      SCORE_SORT_STORAGE_KEY,
      TREND_SORT_STORAGE_KEY,
      CARD_SORT_STORAGE_KEY,
      DISPLAY_MODE_STORAGE_KEY,
      PERSPECTIVE_STORAGE_KEY,
    },
  }
}
