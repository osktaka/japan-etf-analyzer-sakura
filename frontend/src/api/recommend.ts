/** Recommendation API functions */
import apiClient from './client'
import {
  ApiResponse,
  Perspective,
  Recommendation,
  CustomWeights,
} from './types'

let perspectivesCache: Promise<Perspective[]> | null = null

export function getPerspectives(): Promise<Perspective[]> {
  if (!perspectivesCache) {
    perspectivesCache = apiClient
      .get<ApiResponse<Perspective[]>>('/perspectives')
      .then((res) => res.data.data)
      .catch((err) => {
        perspectivesCache = null
        throw err
      })
  }
  return perspectivesCache
}

export async function getRecommendations(
  perspective: string = 'popular',
  limit: number = 5,
  scoringMode: 'full' | 'partial' = 'full',
  customWeights?: CustomWeights | null
): Promise<Recommendation> {
  let url = `/recommendations?perspective=${perspective}&limit=${limit}&scoring_mode=${scoringMode}`
  if (customWeights) {
    // customWeights は既に 0-1 形式のためそのまま送信
    url += `&custom_weights=${encodeURIComponent(JSON.stringify(customWeights))}`
  }
  const response = await apiClient.get<ApiResponse<Recommendation>>(url)
  return response.data.data
}

export const recommendApi = {
  getPerspectives,
  getRecommendations,
}
