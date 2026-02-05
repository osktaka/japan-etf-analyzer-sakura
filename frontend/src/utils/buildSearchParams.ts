/** SearchParams construction helper */
import type { SearchParams, SortField, SortOrder } from '../api'
import type { CustomWeights } from '../api'

export interface BuildSearchParamsOptions {
  currentFilters: SearchParams
  currentKeyword: string
  currentSort: SortField
  currentOrder: SortOrder
  currentPage: number
  returnType: 'price' | 'regression'
  scoringMode: 'full' | 'partial'
  perspective?: string
  customWeights?: CustomWeights | null
  pageSize: number
  favoritesOnly: boolean
  holdingsOnly: boolean
  compareOnly: boolean
  favoriteCodes: Set<string>
  holdingCodes: Set<string>
  compareCodes: string[]
}

/**
 * SearchParamsオブジェクトを構築する共通ヘルパー関数
 *
 * TopPage.tsxの9箇所で重複していたSearchParams構築ロジックを抽出。
 * favoritesOnly/holdingsOnly/compareOnlyの優先順位を一元管理。
 */
export function buildSearchParams(
  options: BuildSearchParamsOptions
): SearchParams {
  const {
    currentFilters,
    currentKeyword,
    currentSort,
    currentOrder,
    currentPage,
    returnType,
    scoringMode,
    perspective,
    customWeights,
    pageSize,
    favoritesOnly,
    holdingsOnly,
    compareOnly,
    favoriteCodes,
    holdingCodes,
    compareCodes,
  } = options

  const searchParams: SearchParams = {
    ...currentFilters,
    keyword: currentKeyword || undefined,
    sort: currentSort,
    order: currentOrder,
    return_type: returnType,
    scoring_mode: scoringMode,
    perspective: perspective,
    limit: pageSize,
    offset: (currentPage - 1) * pageSize,
  }

  // Add custom_weights as JSON string if provided and sorting by custom score
  // customWeights は既に 0-1 形式のためそのまま送信
  if (currentSort === 'score_custom' && customWeights) {
    searchParams.custom_weights = JSON.stringify(customWeights)
  }

  // 優先順位: compareOnly > holdingsOnly > favoritesOnly（排他的に適用）
  if (compareOnly) {
    searchParams.favorite_codes = compareCodes
  } else if (holdingsOnly) {
    searchParams.holding_codes = Array.from(holdingCodes)
  } else if (favoritesOnly) {
    searchParams.favorite_codes = Array.from(favoriteCodes)
  }

  return searchParams
}
