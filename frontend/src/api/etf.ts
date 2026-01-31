/** ETF API functions */
import apiClient from './client'
import {
  ApiResponse,
  BatchCodesChartData,
  BatchPerformanceData,
  BatchPeriodsChartData,
  BatchScoreData,
  Category,
  ChartData,
  ChartPeriod,
  ETFDetail,
  ETFSummary,
  Tag,
} from './types'

export type SortField =
  | 'code'
  | 'name'
  | 'price'
  | 'dividend_yield'
  | 'expense_ratio'
  | 'total_assets'
  | 'return_1m'
  | 'return_3m'
  | 'return_6m'
  | 'return_1y'
  | 'return_3y'
  | 'return_5y'
  | 'return_10y'
  | 'return_20y'
  | 'score_balance'
  | 'score_dividend'
  | 'score_low_cost'
  | 'score_stability'
  | 'score_volume'
  | 'score_growth'
export type SortOrder = 'asc' | 'desc'

export interface SearchParams {
  keyword?: string
  category_id?: number
  tag_ids?: number[]
  min_dividend_yield?: number
  max_expense_ratio?: number
  favorite_codes?: string[]
  holding_codes?: string[]
  sort?: SortField
  order?: SortOrder
  return_type?: 'price' | 'regression'
  limit?: number
  offset?: number
}

export async function getCategories(): Promise<Category[]> {
  const response = await apiClient.get<ApiResponse<Category[]>>('/categories')
  return response.data.data
}

export async function getTags(): Promise<Tag[]> {
  const response = await apiClient.get<ApiResponse<Tag[]>>('/tags')
  return response.data.data
}

export async function searchETFs(params: SearchParams = {}): Promise<{
  items: ETFSummary[]
  total: number
}> {
  const queryParams = new URLSearchParams()

  if (params.keyword) queryParams.append('keyword', params.keyword)
  if (params.category_id)
    queryParams.append('category_id', String(params.category_id))
  if (params.tag_ids?.length)
    queryParams.append('tag_ids', params.tag_ids.join(','))
  if (params.min_dividend_yield !== undefined)
    queryParams.append('min_dividend_yield', String(params.min_dividend_yield))
  if (params.max_expense_ratio !== undefined)
    queryParams.append('max_expense_ratio', String(params.max_expense_ratio))
  // 空配列の場合も送信して「該当なし」を表示させる
  if (params.favorite_codes !== undefined)
    queryParams.append('favorite_codes', params.favorite_codes.join(','))
  if (params.holding_codes !== undefined)
    queryParams.append('holding_codes', params.holding_codes.join(','))
  if (params.sort) queryParams.append('sort', params.sort)
  if (params.order) queryParams.append('order', params.order)
  if (params.return_type) queryParams.append('return_type', params.return_type)
  if (params.limit) queryParams.append('limit', String(params.limit))
  if (params.offset) queryParams.append('offset', String(params.offset))

  const response = await apiClient.get<ApiResponse<ETFSummary[]>>(
    `/etfs?${queryParams.toString()}`
  )
  return {
    items: response.data.data,
    total: response.data.meta?.total || 0,
  }
}

export async function getETFDetail(code: string): Promise<ETFDetail | null> {
  try {
    const response = await apiClient.get<ApiResponse<ETFDetail>>(
      `/etfs/${code}`
    )
    return response.data.data
  } catch {
    return null
  }
}

export async function getETFChart(
  code: string,
  period: ChartPeriod = '1m'
): Promise<ChartData | null> {
  try {
    const response = await apiClient.get<ApiResponse<ChartData>>(
      `/etfs/${code}/chart?period=${period}`
    )
    return response.data.data
  } catch {
    return null
  }
}

export async function getBatchPerformance(
  codes: string[]
): Promise<BatchPerformanceData> {
  if (codes.length === 0) return {}
  try {
    const response = await apiClient.get<ApiResponse<BatchPerformanceData>>(
      `/etfs/performance/batch?codes=${codes.join(',')}`
    )
    return response.data.data
  } catch {
    return {}
  }
}

/**
 * Get chart data for a single ETF across multiple periods (batch).
 * Reduces N API calls to 1 call for multi-period chart display.
 */
export async function getETFChartBatchPeriods(
  code: string,
  periods: ChartPeriod[]
): Promise<BatchPeriodsChartData | null> {
  if (!code || periods.length === 0) return null
  try {
    const response = await apiClient.get<ApiResponse<BatchPeriodsChartData>>(
      `/etfs/${code}/chart/batch?periods=${periods.join(',')}`
    )
    return response.data.data
  } catch {
    return null
  }
}

/**
 * Get chart data for multiple ETFs with a single period (batch).
 * Reduces N API calls to 1 call for comparison chart display.
 */
export async function getETFsChartBatch(
  codes: string[],
  period: ChartPeriod = '1y'
): Promise<BatchCodesChartData> {
  if (codes.length === 0) return {}
  try {
    const response = await apiClient.get<ApiResponse<BatchCodesChartData>>(
      `/etfs/chart/batch?codes=${codes.join(',')}&period=${period}`
    )
    return response.data.data
  } catch {
    return {}
  }
}

/**
 * Get all 6 perspective scores for multiple ETFs (batch).
 * Reduces N API calls to 1 call for score display.
 */
export async function getBatchScores(
  codes: string[],
  scoringMode: 'full' | 'partial' = 'full'
): Promise<BatchScoreData> {
  if (codes.length === 0) return {}
  try {
    const response = await apiClient.get<ApiResponse<BatchScoreData>>(
      `/etfs/scores/batch?codes=${codes.join(',')}&scoring_mode=${scoringMode}`
    )
    return response.data.data
  } catch {
    return {}
  }
}
