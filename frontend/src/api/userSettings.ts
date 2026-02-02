/** User settings API client */
import { apiClient } from './client'
import { ApiResponse, UserSettings, CustomWeights } from './types'

export const userSettingsApi = {
  async getSettings(): Promise<UserSettings> {
    const response =
      await apiClient.get<ApiResponse<UserSettings>>('/user/settings')
    return response.data.data
  },

  async saveCustomWeights(weights: CustomWeights): Promise<UserSettings> {
    const response = await apiClient.put<ApiResponse<UserSettings>>(
      '/user/settings/custom-weights',
      { weights }
    )
    return response.data.data
  },
}

export default userSettingsApi
