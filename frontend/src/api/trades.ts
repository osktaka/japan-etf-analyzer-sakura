/** Trades API client */
import { apiClient } from './client'
import {
  ApiResponse,
  Trade,
  CreateTradeRequest,
  UpdateTradeRequest,
  TradeFilterOptions,
} from './types'

export const tradesApi = {
  async getAll(
    etfCode?: string,
    options?: TradeFilterOptions
  ): Promise<Trade[]> {
    const params: Record<string, string> = {}
    if (etfCode) {
      params.etf_code = etfCode
    }
    if (options?.startDate) {
      params.start_date = options.startDate
    }
    if (options?.endDate) {
      params.end_date = options.endDate
    }
    if (options?.search) {
      params.search = options.search
    }
    const response = await apiClient.get<ApiResponse<Trade[]>>('/trades', {
      params: Object.keys(params).length > 0 ? params : undefined,
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
