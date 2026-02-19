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

  async getHoldings(options?: { includeSold?: boolean }): Promise<Holding[]> {
    const params = new URLSearchParams()
    if (options?.includeSold) {
      params.append('include_sold', 'true')
    }
    const query = params.toString()
    const response = await apiClient.get<ApiResponse<Holding[]>>(
      `/portfolio/holdings${query ? `?${query}` : ''}`
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
