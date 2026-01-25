/** useETFSearch hook tests */
import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useETFSearch } from '../useETFSearch'
import * as api from '../../api'

vi.mock('../../api', () => ({
  searchETFs: vi.fn(),
}))

const mockSearchResponse = {
  items: [
    {
      code: '1306',
      name: 'NEXT FUNDS TOPIX連動型上場投信',
      category: '国内株式',
      expense_ratio: 0.088,
      dividend_yield: 2.15,
      market_price: 2345,
      tags: [],
    },
  ],
  total: 1,
}

describe('useETFSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初期状態ではデータが空', () => {
    const { result } = renderHook(() => useETFSearch())

    expect(result.current.items).toEqual([])
    expect(result.current.total).toBe(0)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('検索実行時にAPIが呼ばれる', async () => {
    vi.mocked(api.searchETFs).mockResolvedValue(mockSearchResponse)
    const { result } = renderHook(() => useETFSearch())

    await act(async () => {
      result.current.search({ keyword: 'TOPIX' })
    })

    await waitFor(() => {
      expect(api.searchETFs).toHaveBeenCalledWith({ keyword: 'TOPIX' })
      expect(result.current.items).toHaveLength(1)
      expect(result.current.total).toBe(1)
    })
  })

  it('検索中はisLoadingがtrue', async () => {
    let resolvePromise: (value: typeof mockSearchResponse) => void
    vi.mocked(api.searchETFs).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      })
    )
    const { result } = renderHook(() => useETFSearch())

    act(() => {
      result.current.search({ keyword: 'TOPIX' })
    })

    expect(result.current.isLoading).toBe(true)

    await act(async () => {
      resolvePromise!(mockSearchResponse)
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('APIエラー時にエラー状態になる', async () => {
    vi.mocked(api.searchETFs).mockRejectedValue(new Error('API Error'))
    const { result } = renderHook(() => useETFSearch())

    await act(async () => {
      result.current.search({ keyword: 'test' })
    })

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
      expect(result.current.error?.message).toBe('API Error')
    })
  })

  it('resetで状態がクリアされる', async () => {
    vi.mocked(api.searchETFs).mockResolvedValue(mockSearchResponse)
    const { result } = renderHook(() => useETFSearch())

    await act(async () => {
      result.current.search({ keyword: 'TOPIX' })
    })

    await waitFor(() => {
      expect(result.current.items).toHaveLength(1)
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.items).toEqual([])
    expect(result.current.total).toBe(0)
  })

  it('パラメータなしで検索実行', async () => {
    vi.mocked(api.searchETFs).mockResolvedValue(mockSearchResponse)
    const { result } = renderHook(() => useETFSearch())

    await act(async () => {
      result.current.search()
    })

    await waitFor(() => {
      expect(api.searchETFs).toHaveBeenCalledWith({})
    })
  })

  it('未知のエラーがErrorオブジェクトに変換される', async () => {
    vi.mocked(api.searchETFs).mockRejectedValue('String error')
    const { result } = renderHook(() => useETFSearch())

    await act(async () => {
      result.current.search({ keyword: 'test' })
    })

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
      expect(result.current.error?.message).toBe('Unknown error')
    })
  })
})
