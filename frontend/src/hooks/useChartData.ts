/** Hook for fetching chart data */
import { useState, useEffect, useCallback } from 'react'
import { getETFChart, ChartData, ChartPeriod } from '../api'

interface UseChartDataState {
  data: ChartData | null
  isLoading: boolean
  error: Error | null
}

export function useChartData(code: string | null, period: ChartPeriod = '1m') {
  const [state, setState] = useState<UseChartDataState>({
    data: null,
    isLoading: false,
    error: null,
  })

  const fetchData = useCallback(async () => {
    if (!code) {
      setState({ data: null, isLoading: false, error: null })
      return
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      const data = await getETFChart(code, period)
      if (data) {
        setState({ data, isLoading: false, error: null })
      } else {
        setState({
          data: null,
          isLoading: false,
          error: new Error('Chart data not found'),
        })
      }
    } catch (err) {
      setState({
        data: null,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      })
    }
  }, [code, period])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { ...state, refetch: fetchData }
}
