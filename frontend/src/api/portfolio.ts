/** Portfolio API client */
import { apiClient } from './client'
import {
  ApiResponse,
  Holding,
  PortfolioSummary,
  ValuationHistory,
  ValuationHistoryPeriod,
} from './types'

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

  async getValuationHistory(
    period: ValuationHistoryPeriod = '1y'
  ): Promise<ValuationHistory> {
    const response = await apiClient.get<ApiResponse<ValuationHistory>>(
      `/portfolio/valuation-history?period=${period}`
    )
    return response.data.data
  },
}

export default portfolioApi
