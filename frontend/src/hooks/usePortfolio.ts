/** Portfolio hook for managing user's holdings and P&L */
import { useCallback, useEffect, useState } from 'react'
import { portfolioApi } from '../api/portfolio'
import { Holding, PortfolioSummary } from '../api/types'
import { useAuth } from './useAuth'

interface UsePortfolioReturn {
  holdings: Holding[]
  summary: PortfolioSummary | null
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export function usePortfolio(): UsePortfolioReturn {
  const { isAuthenticated } = useAuth()
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchPortfolio = useCallback(async () => {
    if (!isAuthenticated) {
      setHoldings([])
      setSummary(null)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [holdingsData, summaryData] = await Promise.all([
        portfolioApi.getHoldings(),
        portfolioApi.getSummary(),
      ])
      setHoldings(holdingsData)
      setSummary(summaryData)
    } catch (err) {
      setError('ポートフォリオの取得に失敗しました')
      console.error('Failed to fetch portfolio:', err)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    fetchPortfolio()
  }, [fetchPortfolio])

  return {
    holdings,
    summary,
    isLoading,
    error,
    refresh: fetchPortfolio,
  }
}

export default usePortfolio
