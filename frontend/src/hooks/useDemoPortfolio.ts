/** Hook for fetching demo portfolio data */
import { useCallback, useEffect, useState } from 'react'
import { demoApi } from '../api/demo'
import { Holding, PortfolioSummary } from '../api/types'

interface UseDemoPortfolioReturn {
  holdings: Holding[]
  summary: PortfolioSummary | null
  isLoading: boolean
  error: string | null
  includeSold: boolean
  setIncludeSold: (value: boolean) => void
  refresh: () => Promise<void>
}

export function useDemoPortfolio(): UseDemoPortfolioReturn {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includeSold, setIncludeSoldState] = useState(() => {
    return localStorage.getItem('holdings-include-sold') === 'true'
  })
  const setIncludeSold = useCallback((value: boolean) => {
    localStorage.setItem('holdings-include-sold', String(value))
    setIncludeSoldState(value)
  }, [])

  const fetchPortfolio = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const [holdingsData, summaryData] = await Promise.all([
        demoApi.getHoldings({ includeSold }),
        demoApi.getPortfolioSummary(),
      ])
      setHoldings(holdingsData)
      setSummary(summaryData)
    } catch (err) {
      setError('デモポートフォリオの取得に失敗しました')
      console.error('Failed to fetch demo portfolio:', err)
    } finally {
      setIsLoading(false)
    }
  }, [includeSold])

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

export default useDemoPortfolio
