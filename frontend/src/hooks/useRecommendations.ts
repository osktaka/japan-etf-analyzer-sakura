/** Hook for fetching recommendations */
import { useState, useEffect, useCallback } from 'react'
import { getRecommendations, Recommendation, CustomWeights } from '../api'

interface UseRecommendationsState {
  data: Recommendation | null
  isLoading: boolean
  error: Error | null
}

export function useRecommendations(
  perspective: string = 'popular',
  scoringMode: 'full' | 'partial' = 'full',
  customWeights?: CustomWeights | null
) {
  const [state, setState] = useState<UseRecommendationsState>({
    data: null,
    isLoading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      const data = await getRecommendations(
        perspective,
        5,
        scoringMode,
        customWeights
      )
      setState({ data, isLoading: false, error: null })
    } catch (err) {
      setState({
        data: null,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      })
    }
  }, [perspective, scoringMode, customWeights])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { ...state, refetch: fetchData }
}
