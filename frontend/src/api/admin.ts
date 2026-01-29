/** Admin API client */
import { apiClient } from './client'
import { ApiResponse, User } from './types'

export interface BatchLog {
  id: number
  batch_name: string
  status: 'running' | 'success' | 'failed'
  started_at: string
  finished_at: string | null
  error_message: string | null
  created_at: string
}

export interface StockSplit {
  id: number
  etf_code: string
  split_date: string
  ratio: number
  is_applied: boolean
  detected_at: string
  reviewed_at: string | null
  reviewed_by: number | null
  previous_close: number | null
  current_close: number | null
  change_percent: number | null
  created_at: string
  updated_at: string
}

export const adminApi = {
  async getUsers(): Promise<User[]> {
    const response = await apiClient.get<ApiResponse<User[]>>('/admin/users')
    return response.data.data
  },

  async updateUserAdmin(userId: number, isAdmin: boolean): Promise<User> {
    const response = await apiClient.patch<ApiResponse<User>>(
      `/admin/users/${userId}`,
      { is_admin: isAdmin }
    )
    return response.data.data
  },

  async getBatchLogs(): Promise<BatchLog[]> {
    const response =
      await apiClient.get<ApiResponse<BatchLog[]>>('/admin/batch-logs')
    return response.data.data
  },

  async getStockSplits(): Promise<StockSplit[]> {
    const response = await apiClient.get<ApiResponse<StockSplit[]>>(
      '/admin/stock-splits'
    )
    return response.data.data
  },

  async toggleStockSplitApplied(
    splitId: number,
    isApplied: boolean
  ): Promise<StockSplit> {
    const response = await apiClient.patch<ApiResponse<StockSplit>>(
      `/admin/stock-splits/${splitId}`,
      { is_applied: isApplied }
    )
    return response.data.data
  },
}

export default adminApi
