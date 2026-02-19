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
  includeSold: boolean
  setIncludeSold: (value: boolean) => void
  refresh: () => Promise<void>
}

export function usePortfolio(options?: {
  skipSummary?: boolean
}): UsePortfolioReturn {
  const { isAuthenticated } = useAuth()
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includeSold, setIncludeSold] = useState(false)

  const fetchPortfolio = useCallback(async () => {
    if (!isAuthenticated) {
      setHoldings([])
      setSummary(null)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      if (options?.skipSummary) {
        const holdingsData = await portfolioApi.getHoldings({ includeSold })
        setHoldings(holdingsData)
      } else {
        const [holdingsData, summaryData] = await Promise.all([
          portfolioApi.getHoldings({ includeSold }),
          portfolioApi.getSummary(),
        ])
        setHoldings(holdingsData)
        setSummary(summaryData)
      }
    } catch (err) {
      setError('ポートフォリオの取得に失敗しました')
      console.error('Failed to fetch portfolio:', err)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, options?.skipSummary, includeSold])

  useEffect(() => {
    fetchPortfolio()
  }, [fetchPortfolio])

  return {
    holdings,
    summary,
    isLoading,
    error,
    includeSold,
    setIncludeSold,
    refresh: fetchPortfolio,
  }
}

export default usePortfolio
