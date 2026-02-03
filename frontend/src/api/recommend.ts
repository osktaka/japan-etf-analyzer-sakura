/** Recommendation API functions */
import apiClient from './client'
import {
  ApiResponse,
  Perspective,
  Recommendation,
  CustomWeights,
} from './types'

export async function getPerspectives(): Promise<Perspective[]> {
  const response =
    await apiClient.get<ApiResponse<Perspective[]>>('/perspectives')
  return response.data.data
}

export async function getRecommendations(
  perspective: string = 'popular',
  limit: number = 5,
  scoringMode: 'full' | 'partial' = 'full',
  customWeights?: CustomWeights | null
): Promise<Recommendation> {
  let url = `/recommendations?perspective=${perspective}&limit=${limit}&scoring_mode=${scoringMode}`
  if (customWeights) {
    url += `&custom_weights=${encodeURIComponent(JSON.stringify(customWeights))}`
  }
  const response = await apiClient.get<ApiResponse<Recommendation>>(url)
  return response.data.data
}

export const recommendApi = {
  getPerspectives,
  getRecommendations,
}
