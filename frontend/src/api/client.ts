/** API client configuration */
import axios, { AxiosInstance, AxiosError } from 'axios'
import { ApiError } from './types'

const isProd = import.meta.env.PROD
const API_BASE_URL = isProd
  ? '/japan-etf-analyzer'
  : import.meta.env.VITE_API_URL || 'http://localhost:8902'

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    // 401は未ログイン状態では期待される動作なのでログ出力しない
    if (error.response?.status === 401) {
      return Promise.reject(error)
    }
    if (error.response) {
      const message = error.response.data?.error?.message || 'An error occurred'
      console.error(`API Error: ${message}`)
    } else if (error.request) {
      console.error('Network Error: No response received')
    } else {
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export default apiClient
