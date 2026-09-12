import { api } from './api'
import type { AuthResponse, LoginCredentials, RegisterCredentials, User } from '@/types/auth'

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const data = await api.post<AuthResponse>('/auth/login', credentials)
    if (data.access_token) {
      localStorage.setItem('cinetrack_token', data.access_token)
    }
    return data
  },

  register: async (credentials: RegisterCredentials): Promise<AuthResponse> => {
    const data = await api.post<AuthResponse>('/auth/register', credentials)
    if (data.access_token) {
      localStorage.setItem('cinetrack_token', data.access_token)
    }
    return data
  },

  getMe: (): Promise<User> => api.get<User>('/auth/me'),

  logout: () => {
    localStorage.removeItem('cinetrack_token')
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('cinetrack_token')
  },
}
