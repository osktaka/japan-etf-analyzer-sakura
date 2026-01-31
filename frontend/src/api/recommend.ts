/** Recommendation API functions */
import apiClient from './client'
import { ApiResponse, Perspective, Recommendation } from './types'

export async function getPerspectives(): Promise<Perspective[]> {
  const response =
    await apiClient.get<ApiResponse<Perspective[]>>('/perspectives')
  return response.data.data
}

export async function getRecommendations(
  perspective: string = 'popular',
  limit: number = 5,
  scoringMode: 'full' | 'partial' = 'full'
): Promise<Recommendation> {
  const response = await apiClient.get<ApiResponse<Recommendation>>(
    `/recommendations?perspective=${perspective}&limit=${limit}&scoring_mode=${scoringMode}`
  )
  return response.data.data
}
