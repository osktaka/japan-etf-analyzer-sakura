/** Hook for fetching demo favorites data */
import { useCallback, useEffect, useState } from 'react'
import { demoApi } from '../api/demo'
import { Favorite } from '../api/types'

interface UseDemoFavoritesReturn {
  favorites: Favorite[]
  isLoading: boolean
  error: string | null
  refresh: (perspective?: string) => Promise<void>
}

export function useDemoFavorites(
  initialPerspective: string = 'balance'
): UseDemoFavoritesReturn {
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchFavorites = useCallback(
    async (perspective: string = initialPerspective) => {
      setIsLoading(true)
      setError(null)

      try {
        const data = await demoApi.getFavorites(perspective, 'full')
        setFavorites(data)
      } catch (err) {
        setError('デモお気に入りの取得に失敗しました')
        console.error('Failed to fetch demo favorites:', err)
      } finally {
        setIsLoading(false)
      }
    },
    [initialPerspective]
  )

  useEffect(() => {
    fetchFavorites()
  }, [fetchFavorites])

  return {
    favorites,
    isLoading,
    error,
    refresh: fetchFavorites,
  }
}

export default useDemoFavorites
