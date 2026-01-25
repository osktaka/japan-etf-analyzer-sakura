/** Portfolio API client */
import { apiClient } from './client'
import { ApiResponse, Holding, PortfolioSummary } from './types'

export const portfolioApi = {
  async getSummary(): Promise<PortfolioSummary> {
    const response =
      await apiClient.get<ApiResponse<PortfolioSummary>>('/portfolio')
    return response.data.data
  },

  async getHoldings(): Promise<Holding[]> {
    const response = await apiClient.get<ApiResponse<Holding[]>>(
      '/portfolio/holdings'
    )
    return response.data.data
  },
}

export default portfolioApi
