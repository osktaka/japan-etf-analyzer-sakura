/** Hook for fetching portfolio valuation history */
import { useCallback, useEffect, useRef, useState } from 'react'
import { portfolioApi } from '../api/portfolio'
import { ValuationHistory, ValuationHistoryPeriod } from '../api/types'
import { useAuth } from './useAuth'

interface UsePortfolioHistoryReturn {
  data: ValuationHistory
  isLoading: boolean
  error: string | null
  period: ValuationHistoryPeriod
  setPeriod: (period: ValuationHistoryPeriod) => void
  refresh: () => Promise<void>
}

export function usePortfolioHistory(
  initialPeriod: ValuationHistoryPeriod = '1y'
): UsePortfolioHistoryReturn {
  const { isAuthenticated } = useAuth()
  const [data, setData] = useState<ValuationHistory>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const VALID_PERIODS: ValuationHistoryPeriod[] = ['1m', '3m', '6m', '1y', '3y', '5y', '10y', '20y']

  const [period, setPeriodState] = useState<ValuationHistoryPeriod>(() => {
    try {
      const saved = localStorage.getItem('portfolio-history-period')
      if (saved && VALID_PERIODS.includes(saved as ValuationHistoryPeriod)) {
        return saved as ValuationHistoryPeriod
      }
    } catch {
      // ストレージアクセスエラー時はデフォルト値
    }
    return initialPeriod
  })

  const setPeriod = useCallback((p: ValuationHistoryPeriod) => {
    try {
      localStorage.setItem('portfolio-history-period', p)
    } catch {
      // 保存失敗時は無視
    }
    setPeriodState(p)
  }, [])

  // キャッシュ: period別にデータを保持
  const cacheRef = useRef<Map<ValuationHistoryPeriod, ValuationHistory>>(
    new Map()
  )

  const fetchHistory = useCallback(async () => {
    if (!isAuthenticated) {
      setData([])
      return
    }

    // キャッシュチェック
    const cached = cacheRef.current.get(period)
    if (cached) {
      setData(cached)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const history = await portfolioApi.getValuationHistory(period)
      setData(history)
      // キャッシュに保存
      cacheRef.current.set(period, history)
    } catch (err) {
      setError('評価額履歴の取得に失敗しました')
      console.error('Failed to fetch valuation history:', err)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, period])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // refresh時はキャッシュをクリア
  const refresh = useCallback(async () => {
    cacheRef.current.clear()
    await fetchHistory()
  }, [fetchHistory])

  return {
    data,
    isLoading,
    error,
    period,
    setPeriod,
    refresh,
  }
}

export default usePortfolioHistory
