import apiClient from '@/lib/api-client';
import type {
  AuthTokens,
  LoginRequest,
  RegisterRequest,
  User,
} from '@/types';

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>('/auth/login', data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>('/auth/register', data);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};
