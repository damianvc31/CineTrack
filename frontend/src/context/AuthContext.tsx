import React, { createContext, useContext, useEffect, useState } from 'react'
import type { User, LoginCredentials, RegisterCredentials } from '@/types/auth'
import { authService } from '@/services/authService'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  updateUser: (updatedUser: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  const refreshUser = async () => {
    if (!authService.isAuthenticated()) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const userData = await authService.getMe()
      setUser(userData)
    } catch {
      authService.logout()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshUser()
  }, [])

  const clearRecommendationsCache = () => {
    try {
      sessionStorage.removeItem('cinetrack_recs_cache')
    } catch {
      // ignore
    }
  }

  const login = async (credentials: LoginCredentials) => {
    setLoading(true)
    try {
      const res = await authService.login(credentials)
      clearRecommendationsCache()
      setUser(res.user)
    } finally {
      setLoading(false)
    }
  }

  const register = async (credentials: RegisterCredentials) => {
    setLoading(true)
    try {
      const res = await authService.register(credentials)
      clearRecommendationsCache()
      setUser(res.user)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    authService.logout()
    clearRecommendationsCache()
    setUser(null)
  }

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
