import apiClient from './client'
import type { ApiResponse, TagMomentumResponse } from './types'

export async function getTagMomentum(
  category?: string
): Promise<TagMomentumResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : ''
  const response = await apiClient.get<ApiResponse<TagMomentumResponse>>(
    `/market/tag-momentum${params}`
  )
  return response.data.data
}
