/** Hook for fetching portfolio valuation history */
import { useCallback, useEffect, useState } from 'react'
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
  const [period, setPeriod] = useState<ValuationHistoryPeriod>(initialPeriod)

  const fetchHistory = useCallback(async () => {
    if (!isAuthenticated) {
      setData([])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const history = await portfolioApi.getValuationHistory(period)
      setData(history)
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

  return {
    data,
    isLoading,
    error,
    period,
    setPeriod,
    refresh: fetchHistory,
  }
}

export default usePortfolioHistory
