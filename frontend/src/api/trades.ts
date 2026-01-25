/** Trades API client */
import { apiClient } from './client'
import {
  ApiResponse,
  Trade,
  CreateTradeRequest,
  UpdateTradeRequest,
} from './types'

export const tradesApi = {
  async getAll(etfCode?: string): Promise<Trade[]> {
    const params = etfCode ? { etf_code: etfCode } : undefined
    const response = await apiClient.get<ApiResponse<Trade[]>>('/trades', {
      params,
    })
    return response.data.data
  },

  async getById(tradeId: number): Promise<Trade> {
    const response = await apiClient.get<ApiResponse<Trade>>(
      `/trades/${tradeId}`
    )
    return response.data.data
  },

  async create(data: CreateTradeRequest): Promise<Trade> {
    const response = await apiClient.post<ApiResponse<Trade>>('/trades', data)
    return response.data.data
  },

  async update(tradeId: number, data: UpdateTradeRequest): Promise<Trade> {
    const response = await apiClient.put<ApiResponse<Trade>>(
      `/trades/${tradeId}`,
      data
    )
    return response.data.data
  },

  async delete(tradeId: number): Promise<void> {
    await apiClient.delete(`/trades/${tradeId}`)
  },
}

export default tradesApi
