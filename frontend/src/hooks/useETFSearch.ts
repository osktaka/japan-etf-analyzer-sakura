/** Hook for ETF search */
import { useState, useCallback } from 'react'
import { searchETFs, ETFSummary, SearchParams } from '../api'

interface UseETFSearchState {
  items: ETFSummary[]
  total: number
  isLoading: boolean
  error: Error | null
}

export function useETFSearch() {
  const [state, setState] = useState<UseETFSearchState>({
    items: [],
    total: 0,
    isLoading: false,
    error: null,
  })

  const search = useCallback(async (params: SearchParams = {}) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      const result = await searchETFs(params)
      setState({
        items: result.items,
        total: result.total,
        isLoading: false,
        error: null,
      })
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      }))
    }
  }, [])

  const reset = useCallback(() => {
    setState({ items: [], total: 0, isLoading: false, error: null })
  }, [])

  return { ...state, search, reset }
}
