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
}

export default adminApi
