/** useFavorites hook tests */
import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFavorites } from '../useFavorites'
import { favoritesApi } from '../../api/favorites'
import * as useAuthModule from '../useAuth'

vi.mock('../../api/favorites', () => ({
  favoritesApi: {
    getAll: vi.fn(),
    getCodes: vi.fn(),
    add: vi.fn(),
    remove: vi.fn(),
  },
}))

vi.mock('../useAuth', () => ({
  useAuth: vi.fn(),
}))

const mockFavorite = {
  id: 1,
  etf_code: '1306',
  created_at: '2025-01-01',
  etf: {
    code: '1306',
    name: 'TOPIX ETF',
    category: '国内株式',
    expense_ratio: 0.1,
    dividend_yield: 2.0,
    market_price: 2000,
    tags: [],
  },
}

describe('useFavorites', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
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
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    })
  })

  it('認証済みの場合、初期化時にお気に入りを取得', async () => {
    vi.mocked(favoritesApi.getAll).mockResolvedValue([mockFavorite])
    vi.mocked(favoritesApi.getCodes).mockResolvedValue(['1306'])

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.favorites).toHaveLength(1)
      expect(result.current.favoriteCodes.has('1306')).toBe(true)
    })
  })

  it('未認証の場合、お気に入りは空', async () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isAdmin: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    })

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.favorites).toEqual([])
      expect(result.current.favoriteCodes.size).toBe(0)
    })
  })

  it('isFavoriteが正しく判定される', async () => {
    vi.mocked(favoritesApi.getAll).mockResolvedValue([mockFavorite])
    vi.mocked(favoritesApi.getCodes).mockResolvedValue(['1306'])

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.isFavorite('1306')).toBe(true)
      expect(result.current.isFavorite('9999')).toBe(false)
    })
  })

  it('addFavoriteが成功する', async () => {
    vi.mocked(favoritesApi.getAll).mockResolvedValue([])
    vi.mocked(favoritesApi.getCodes).mockResolvedValue([])
    vi.mocked(favoritesApi.add).mockResolvedValue(mockFavorite)

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    let success: boolean
    await act(async () => {
      success = await result.current.addFavorite('1306')
    })

    expect(success!).toBe(true)
    expect(result.current.favorites).toHaveLength(1)
    expect(result.current.favoriteCodes.has('1306')).toBe(true)
  })

  it('removeFavoriteが成功する', async () => {
    vi.mocked(favoritesApi.getAll).mockResolvedValue([mockFavorite])
    vi.mocked(favoritesApi.getCodes).mockResolvedValue(['1306'])
    vi.mocked(favoritesApi.remove).mockResolvedValue()

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.favorites).toHaveLength(1)
    })

    let success: boolean
    await act(async () => {
      success = await result.current.removeFavorite('1306')
    })

    expect(success!).toBe(true)
    expect(result.current.favorites).toHaveLength(0)
    expect(result.current.favoriteCodes.has('1306')).toBe(false)
  })

  it('toggleFavoriteがお気に入り追加/削除を切り替える', async () => {
    vi.mocked(favoritesApi.getAll).mockResolvedValue([])
    vi.mocked(favoritesApi.getCodes).mockResolvedValue([])
    vi.mocked(favoritesApi.add).mockResolvedValue(mockFavorite)
    vi.mocked(favoritesApi.remove).mockResolvedValue()

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // 追加
    await act(async () => {
      await result.current.toggleFavorite('1306')
    })
    expect(result.current.favoriteCodes.has('1306')).toBe(true)

    // 削除
    await act(async () => {
      await result.current.toggleFavorite('1306')
    })
    expect(result.current.favoriteCodes.has('1306')).toBe(false)
  })

  it('未認証時にaddFavoriteがfalseを返す', async () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isAdmin: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    })

    const { result } = renderHook(() => useFavorites())

    let success: boolean
    await act(async () => {
      success = await result.current.addFavorite('1306')
    })

    expect(success!).toBe(false)
  })

  it('API取得エラー時にエラー状態になる', async () => {
    vi.mocked(favoritesApi.getAll).mockRejectedValue(new Error('API Error'))
    vi.mocked(favoritesApi.getCodes).mockRejectedValue(new Error('API Error'))

    const { result } = renderHook(() => useFavorites())

    await waitFor(() => {
      expect(result.current.error).toBe('お気に入りの取得に失敗しました')
    })
  })
})
