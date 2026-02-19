/** Demo API client */
import { apiClient } from './client'
import {
  ApiResponse,
  Favorite,
  Holding,
  PortfolioSummary,
  Trade,
} from './types'

export const demoApi = {
  async getPortfolioSummary(): Promise<PortfolioSummary> {
    const response =
      await apiClient.get<ApiResponse<PortfolioSummary>>('/demo/portfolio')
    return response.data.data
  },

  async getHoldings(options?: { includeSold?: boolean }): Promise<Holding[]> {
    const params = new URLSearchParams()
    if (options?.includeSold) {
      params.append('include_sold', 'true')
    }
    const query = params.toString()
    const response = await apiClient.get<ApiResponse<Holding[]>>(
      `/demo/portfolio/holdings${query ? `?${query}` : ''}`
    )
    return response.data.data
  },

  async getTrades(): Promise<Trade[]> {
    const response = await apiClient.get<ApiResponse<Trade[]>>('/demo/trades')
    return response.data.data
  },

  async getFavorites(
    perspective: string = 'balance',
    scoringMode: 'full' | 'partial' = 'full'
  ): Promise<Favorite[]> {
    const queryParams = new URLSearchParams()
    if (perspective) queryParams.append('perspective', perspective)
    if (scoringMode) queryParams.append('scoring_mode', scoringMode)

    const response = await apiClient.get<ApiResponse<Favorite[]>>(
      `/demo/favorites?${queryParams.toString()}`
    )
    return response.data.data
  },
}

export default demoApi
