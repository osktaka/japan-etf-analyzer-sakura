/** useAuth hook tests */
import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useAuth } from '../useAuth'
import { AuthContext, AuthContextValue } from '../../contexts/AuthContext'
import { ReactNode } from 'react'

describe('useAuth', () => {
  const createWrapper = (value: AuthContextValue) => {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
      )
    }
  }

  it('コンテキストの値を返す', () => {
    const mockValue: AuthContextValue = {
      user: {
        id: 1,
        user_id: 'testuser',
        username: 'test',
        is_active: true,
        is_admin: false,
        created_at: '2025-01-01',
      },
      isLoading: false,
      isAuthenticated: true,
      isAdmin: false,
      login: async () => {},
      register: async () => {},
      logout: async () => {},
      checkAuth: async () => {},
    }

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    })

    expect(result.current.user).toEqual(mockValue.user)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isLoading).toBe(false)
  })

  it('未認証状態を正しく返す', () => {
    const mockValue: AuthContextValue = {
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isAdmin: false,
      login: async () => {},
      register: async () => {},
      logout: async () => {},
      checkAuth: async () => {},
    }

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    })

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('ローディング状態を正しく返す', () => {
    const mockValue: AuthContextValue = {
      user: null,
      isLoading: true,
      isAuthenticated: false,
      isAdmin: false,
      login: async () => {},
      register: async () => {},
      logout: async () => {},
      checkAuth: async () => {},
    }

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    })

    expect(result.current.isLoading).toBe(true)
  })

  it('AuthProvider外で使用するとエラーをスローする', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => {
      renderHook(() => useAuth())
    }).toThrow('useAuth must be used within an AuthProvider')

    consoleSpy.mockRestore()
  })
})
