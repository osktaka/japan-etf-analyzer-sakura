/** Authentication API client */
import { apiClient } from './client';
import { ApiResponse, LoginRequest, RegisterRequest, User } from './types';

export const authApi = {
  async register(data: RegisterRequest): Promise<User> {
    const response = await apiClient.post<ApiResponse<User>>(
      '/auth/register',
      data
    );
    return response.data.data;
  },

  async login(data: LoginRequest): Promise<User> {
    const response = await apiClient.post<ApiResponse<User>>(
      '/auth/login',
      data
    );
    return response.data.data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await apiClient.get<ApiResponse<User>>('/auth/me');
      return response.data.data;
    } catch {
      return null;
    }
  },
};

export default authApi;
