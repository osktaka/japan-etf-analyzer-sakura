/** Compare API */
import { apiClient } from './client'
import {
  ApiResponse,
  PerformanceComparison,
  ETFPerformance,
  CustomWeights,
} from './types'

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

/** Score data for a single ETF in comparison */
export interface CompareScoreItem {
  score: number | null
  axis_scores: Record<string, number | null> | null
}

/** Scores keyed by ETF code */
export type CompareScores = Record<string, CompareScoreItem>

/**
 * Get evaluation scores for multiple ETFs
 */
export async function getCompareScores(
  codes: string[],
  perspective: string = 'balance',
  scoringMode: 'full' | 'partial' = 'full',
  customWeights?: CustomWeights | null
): Promise<CompareScores | null> {
  try {
    let url = `/compare/scores?codes=${codes.join(',')}&perspective=${perspective}&scoring_mode=${scoringMode}`
    if (customWeights) {
      url += `&custom_weights=${encodeURIComponent(JSON.stringify(customWeights))}`
    }
    const response = await apiClient.get<ApiResponse<CompareScores>>(url)
    return response.data.data
  } catch {
    return null
  }
}
