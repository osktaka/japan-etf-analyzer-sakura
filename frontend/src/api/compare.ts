/** Compare API */
import { apiClient } from './client'
import { ApiResponse, PerformanceComparison, ETFPerformance } from './types'

/**
 * Get performance comparison for multiple ETFs
 */
export async function getPerformanceComparison(
  codes: string[]
): Promise<PerformanceComparison | null> {
  try {
    const response = await apiClient.get<ApiResponse<PerformanceComparison>>(
      `/compare/performance?codes=${codes.join(',')}`
    )
    return response.data.data
  } catch {
    return null
  }
}

/**
 * Get performance metrics for a single ETF
 */
export async function getETFPerformance(
  code: string
): Promise<ETFPerformance | null> {
  try {
    const response = await apiClient.get<ApiResponse<ETFPerformance>>(
      `/compare/performance/${code}`
    )
    return response.data.data
  } catch {
    return null
  }
}
