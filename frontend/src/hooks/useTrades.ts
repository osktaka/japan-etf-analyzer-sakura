/** Trades hook for managing user's trade records */
import { useCallback, useEffect, useState } from 'react'
import { tradesApi } from '../api/trades'
import { Trade, CreateTradeRequest, UpdateTradeRequest } from '../api/types'
import { useAuth } from './useAuth'

interface UseTradesReturn {
  trades: Trade[]
  isLoading: boolean
  error: string | null
  createTrade: (data: CreateTradeRequest) => Promise<boolean>
  updateTrade: (id: number, data: UpdateTradeRequest) => Promise<boolean>
  deleteTrade: (id: number) => Promise<boolean>
  refresh: () => Promise<void>
}

export function useTrades(etfCode?: string): UseTradesReturn {
  const { isAuthenticated } = useAuth()
  const [trades, setTrades] = useState<Trade[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTrades = useCallback(async () => {
    if (!isAuthenticated) {
      setTrades([])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const data = await tradesApi.getAll(etfCode)
      setTrades(data)
    } catch (err) {
      setError('取引履歴の取得に失敗しました')
      console.error('Failed to fetch trades:', err)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, etfCode])

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  const createTrade = useCallback(
    async (data: CreateTradeRequest): Promise<boolean> => {
      if (!isAuthenticated) return false

      try {
        const newTrade = await tradesApi.create(data)
        setTrades((prev) => [newTrade, ...prev])
        return true
      } catch (err) {
        console.error('Failed to create trade:', err)
        return false
      }
    },
    [isAuthenticated]
  )

  const updateTrade = useCallback(
    async (id: number, data: UpdateTradeRequest): Promise<boolean> => {
      if (!isAuthenticated) return false

      try {
        const updatedTrade = await tradesApi.update(id, data)
        setTrades((prev) => prev.map((t) => (t.id === id ? updatedTrade : t)))
        return true
      } catch (err) {
        console.error('Failed to update trade:', err)
        return false
      }
    },
    [isAuthenticated]
  )

  const deleteTrade = useCallback(
    async (id: number): Promise<boolean> => {
      if (!isAuthenticated) return false

      try {
        await tradesApi.delete(id)
        setTrades((prev) => prev.filter((t) => t.id !== id))
        return true
      } catch (err) {
        console.error('Failed to delete trade:', err)
        return false
      }
    },
    [isAuthenticated]
  )

  return {
    trades,
    isLoading,
    error,
    createTrade,
    updateTrade,
    deleteTrade,
    refresh: fetchTrades,
  }
}

export default useTrades
