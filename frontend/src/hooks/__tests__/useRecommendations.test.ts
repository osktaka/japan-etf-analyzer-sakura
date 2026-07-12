/** useRecommendations hook tests */
import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useRecommendations } from '../useRecommendations'
import * as api from '../../api'

vi.mock('../../api', () => ({
  getRecommendations: vi.fn(),
}))

const mockRecommendation = {
  perspective: { id: 'popular', name: '人気', description: '人気のETF' },
  items: [
    {
      code: '1306',
      name: 'TOPIX ETF',
      category: '国内株式',
      expense_ratio: 0.1,
      dividend_yield: 2.0,
      market_price: 2000,
      tags: [],
      score: 85.5,
    },
  ],
}

describe('useRecommendations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初期状態でデータを取得', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue(mockRecommendation)
    const { result } = renderHook(() => useRecommendations())

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.data).toEqual(mockRecommendation)
      expect(result.current.isLoading).toBe(false)
    })

    expect(api.getRecommendations).toHaveBeenCalledWith(
      'popular',
      5,
      'full',
      undefined
    )
  })

  it('perspectiveを指定してデータを取得', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue(mockRecommendation)
    const { result } = renderHook(() => useRecommendations('dividend'))

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    expect(api.getRecommendations).toHaveBeenCalledWith(
      'dividend',
      5,
      'full',
      undefined
    )
  })

  it('perspectiveが変わると再取得される', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue(mockRecommendation)
    const { result, rerender } = renderHook(
      ({ perspective }) => useRecommendations(perspective),
      { initialProps: { perspective: 'popular' } }
    )

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    vi.mocked(api.getRecommendations).mockClear()
    rerender({ perspective: 'dividend' })

    await waitFor(() => {
      expect(api.getRecommendations).toHaveBeenCalledWith(
        'dividend',
        5,
        'full',
        undefined
      )
    })
  })

  it('APIエラー時にエラー状態になる', async () => {
    vi.mocked(api.getRecommendations).mockRejectedValue(new Error('API Error'))
    const { result } = renderHook(() => useRecommendations())

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
      expect(result.current.error?.message).toBe('API Error')
    })
  })

  it('未知のエラーがErrorオブジェクトに変換される', async () => {
    vi.mocked(api.getRecommendations).mockRejectedValue('String error')
    const { result } = renderHook(() => useRecommendations())

    await waitFor(() => {
      expect(result.current.error?.message).toBe('Unknown error')
    })
  })

  it('refetchで再取得できる', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue(mockRecommendation)
    const { result } = renderHook(() => useRecommendations())

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    vi.mocked(api.getRecommendations).mockClear()

    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(api.getRecommendations).toHaveBeenCalled()
    })
  })

  it('データ取得中はisLoadingがtrue', async () => {
    let resolvePromise: (value: typeof mockRecommendation) => void
    vi.mocked(api.getRecommendations).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      })
    )

    const { result } = renderHook(() => useRecommendations())

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeNull()

    await act(async () => {
      resolvePromise!(mockRecommendation)
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).not.toBeNull()
    })
  })

  it('エラー後の再取得でエラーがクリアされる', async () => {
    vi.mocked(api.getRecommendations).mockRejectedValueOnce(
      new Error('API Error')
    )
    const { result } = renderHook(() => useRecommendations())

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
    })

    vi.mocked(api.getRecommendations).mockResolvedValueOnce(mockRecommendation)

    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.error).toBeNull()
      expect(result.current.data).not.toBeNull()
    })
  })
})
