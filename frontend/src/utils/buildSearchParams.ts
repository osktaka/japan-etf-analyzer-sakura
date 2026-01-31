/** SearchParams construction helper */
import type { SearchParams, SortField, SortOrder } from '../api'

export interface BuildSearchParamsOptions {
  currentFilters: SearchParams
  currentKeyword: string
  currentSort: SortField
  currentOrder: SortOrder
  currentPage: number
  returnType: 'price' | 'regression'
  scoringMode: 'full' | 'partial'
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
    limit: pageSize,
    offset: (currentPage - 1) * pageSize,
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
