/** useChartData hook tests */
import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useChartData } from '../useChartData'
import * as api from '../../api'

vi.mock('../../api', () => ({
  getETFChart: vi.fn(),
}))

const mockChartData = {
  code: '1306',
  name: 'TOPIX ETF',
  period: '1m',
  data: [
    {
      date: '2025-01-01',
      open: 2300,
      high: 2350,
      low: 2290,
      close: 2340,
      volume: 1000000,
    },
    {
      date: '2025-01-02',
      open: 2340,
      high: 2360,
      low: 2330,
      close: 2355,
      volume: 1200000,
    },
  ],
}

describe('useChartData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('codeがnullの場合、データを取得しない', async () => {
    const { result } = renderHook(() => useChartData(null))

    expect(result.current.data).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(api.getETFChart).not.toHaveBeenCalled()
  })

  it('codeが指定された場合、チャートデータを取得', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(mockChartData)
    const { result } = renderHook(() => useChartData('1306'))

    await waitFor(() => {
      expect(result.current.data).toEqual(mockChartData)
      expect(result.current.isLoading).toBe(false)
    })

    expect(api.getETFChart).toHaveBeenCalledWith('1306', '1m')
  })

  it('periodが指定された場合、そのperiodでデータを取得', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(mockChartData)
    const { result } = renderHook(() => useChartData('1306', '3m'))

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    expect(api.getETFChart).toHaveBeenCalledWith('1306', '3m')
  })

  it('データ取得中はisLoadingがtrue', async () => {
    let resolvePromise: (value: typeof mockChartData) => void
    vi.mocked(api.getETFChart).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      })
    )

    const { result } = renderHook(() => useChartData('1306'))

    expect(result.current.isLoading).toBe(true)

    await act(async () => {
      resolvePromise!(mockChartData)
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('APIエラー時にエラー状態になる', async () => {
    vi.mocked(api.getETFChart).mockRejectedValue(new Error('API Error'))
    const { result } = renderHook(() => useChartData('1306'))

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
      expect(result.current.error?.message).toBe('API Error')
    })
  })

  it('データがnullの場合、エラー状態になる', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(null)
    const { result } = renderHook(() => useChartData('1306'))

    await waitFor(() => {
      expect(result.current.error?.message).toBe('Chart data not found')
    })
  })

  it('refetchで再取得できる', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(mockChartData)
    const { result } = renderHook(() => useChartData('1306'))

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    vi.mocked(api.getETFChart).mockClear()

    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(api.getETFChart).toHaveBeenCalled()
    })
  })

  it('codeが変わると再取得される', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(mockChartData)
    const { result, rerender } = renderHook(({ code }) => useChartData(code), {
      initialProps: { code: '1306' },
    })

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    vi.mocked(api.getETFChart).mockClear()
    rerender({ code: '1321' })

    await waitFor(() => {
      expect(api.getETFChart).toHaveBeenCalledWith('1321', '1m')
    })
  })

  it('periodが変わると再取得される', async () => {
    vi.mocked(api.getETFChart).mockResolvedValue(mockChartData)
    const { result, rerender } = renderHook(
      ({ period }) => useChartData('1306', period),
      { initialProps: { period: '1m' as api.ChartPeriod } }
    )

    await waitFor(() => {
      expect(result.current.data).not.toBeNull()
    })

    vi.mocked(api.getETFChart).mockClear()
    rerender({ period: '3m' as api.ChartPeriod })

    await waitFor(() => {
      expect(api.getETFChart).toHaveBeenCalledWith('1306', '3m')
    })
  })
})
