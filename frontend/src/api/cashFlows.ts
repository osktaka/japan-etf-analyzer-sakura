/** Cash Flows API client */
import { apiClient } from './client'
import {
  ApiResponse,
  CashFlow,
  CreateCashFlowRequest,
  UpdateCashFlowRequest,
} from './types'

export interface CashFlowFilterOptions {
  startDate?: string // YYYY-MM-DD
  endDate?: string // YYYY-MM-DD
}

export const cashFlowsApi = {
  async getAll(options?: CashFlowFilterOptions): Promise<CashFlow[]> {
    const params: Record<string, string> = {}
    if (options?.startDate) {
      params.start_date = options.startDate
    }
    if (options?.endDate) {
      params.end_date = options.endDate
    }
    const response = await apiClient.get<ApiResponse<CashFlow[]>>(
      '/cash-flows',
      {
        params: Object.keys(params).length > 0 ? params : undefined,
      }
    )
    return response.data.data
  },

  async create(data: CreateCashFlowRequest): Promise<CashFlow> {
    const response = await apiClient.post<ApiResponse<CashFlow>>(
      '/cash-flows',
      data
    )
    return response.data.data
  },

  async update(id: number, data: UpdateCashFlowRequest): Promise<CashFlow> {
    const response = await apiClient.put<ApiResponse<CashFlow>>(
      `/cash-flows/${id}`,
      data
    )
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/cash-flows/${id}`)
  },
}

export default cashFlowsApi
