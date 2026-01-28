/** Hook for fetching multiple period chart data with batch API */
import { useState, useEffect, useCallback } from 'react'
import { getETFChartBatchPeriods, ChartData, ChartPeriod } from '../api'

const MULTI_PERIODS: ChartPeriod[] = ['3m', '6m', '1y', '3y', '5y', '10y']

type MultiPeriodChartData = Record<ChartPeriod, ChartData | null>

interface UseMultiPeriodChartDataState {
  data: MultiPeriodChartData
  isLoading: boolean
  error: Error | null
}

const initialData: MultiPeriodChartData = {
  '1m': null,
  '3m': null,
  '6m': null,
  '1y': null,
  '3y': null,
  '5y': null,
  '10y': null,
  '20y': null,
}

export function useMultiPeriodChartData(code: string | null) {
  const [state, setState] = useState<UseMultiPeriodChartDataState>({
    data: initialData,
    isLoading: false,
    error: null,
  })

  const fetchData = useCallback(async () => {
    if (!code) {
      setState({ data: initialData, isLoading: false, error: null })
      return
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      // Single batch API call instead of 6 parallel calls
      const batchResult = await getETFChartBatchPeriods(code, MULTI_PERIODS)

      const newData: MultiPeriodChartData = { ...initialData }
      if (batchResult) {
        MULTI_PERIODS.forEach((period) => {
          const chartPoints = batchResult.charts[period]
          if (chartPoints) {
            newData[period] = {
              code: batchResult.code,
              name: batchResult.name,
              period,
              data: chartPoints,
            }
          }
        })
      }

      setState({ data: newData, isLoading: false, error: null })
    } catch (err) {
      setState({
        data: initialData,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      })
    }
  }, [code])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { ...state, refetch: fetchData, periods: MULTI_PERIODS }
}
