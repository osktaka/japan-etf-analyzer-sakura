/** API client configuration */
import axios, { AxiosInstance, AxiosError } from 'axios';
import { ApiError } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8902';

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response) {
      const message =
        error.response.data?.error?.message || 'An error occurred';
      console.error(`API Error: ${message}`);
    } else if (error.request) {
      console.error('Network Error: No response received');
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
