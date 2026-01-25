/** Favorites API client */
import { apiClient } from './client'
import { ApiResponse, Favorite } from './types'

export const favoritesApi = {
  async getAll(): Promise<Favorite[]> {
    const response = await apiClient.get<ApiResponse<Favorite[]>>('/favorites')
    return response.data.data
  },

  async add(etfCode: string): Promise<Favorite> {
    const response = await apiClient.post<ApiResponse<Favorite>>('/favorites', {
      etf_code: etfCode,
    })
    return response.data.data
  },

  async remove(etfCode: string): Promise<void> {
    await apiClient.delete(`/favorites/${etfCode}`)
  },

  async getCodes(): Promise<string[]> {
    const response =
      await apiClient.get<ApiResponse<string[]>>('/favorites/codes')
    return response.data.data
  },

  async check(etfCode: string): Promise<boolean> {
    const response = await apiClient.get<
      ApiResponse<{ is_favorited: boolean }>
    >(`/favorites/check/${etfCode}`)
    return response.data.data.is_favorited
  },
}

export default favoritesApi
