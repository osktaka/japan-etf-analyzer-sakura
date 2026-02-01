/** Favorites hook */
import { useCallback, useEffect, useState } from 'react'
import { favoritesApi } from '../api/favorites'
import { Favorite } from '../api/types'
import { useAuth } from './useAuth'

interface UseFavoritesReturn {
  favorites: Favorite[]
  favoriteCodes: Set<string>
  isLoading: boolean
  error: string | null
  addFavorite: (etfCode: string) => Promise<boolean>
  removeFavorite: (etfCode: string) => Promise<boolean>
  toggleFavorite: (etfCode: string) => Promise<boolean>
  isFavorite: (etfCode: string) => boolean
  refresh: (perspective?: string, scoringMode?: 'full' | 'partial') => Promise<void>
}

export function useFavorites(
  initialPerspective: string = 'balance',
  initialScoringMode: 'full' | 'partial' = 'full'
): UseFavoritesReturn {
  const { isAuthenticated } = useAuth()
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [favoriteCodes, setFavoriteCodes] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchFavorites = useCallback(
    async (
      perspective: string = initialPerspective,
      scoringMode: 'full' | 'partial' = initialScoringMode
    ) => {
      if (!isAuthenticated) {
        setFavorites([])
        setFavoriteCodes(new Set())
        return
      }

      setIsLoading(true)
      setError(null)

      try {
        const [favoritesData, codesData] = await Promise.all([
          favoritesApi.getAll(perspective, scoringMode),
          favoritesApi.getCodes(),
        ])
        setFavorites(favoritesData)
        setFavoriteCodes(new Set(codesData))
      } catch (err) {
        setError('お気に入りの取得に失敗しました')
        console.error('Failed to fetch favorites:', err)
      } finally {
        setIsLoading(false)
      }
    },
    [isAuthenticated, initialPerspective, initialScoringMode]
  )

  useEffect(() => {
    fetchFavorites()
  }, [fetchFavorites])

  const addFavorite = useCallback(
    async (etfCode: string): Promise<boolean> => {
      if (!isAuthenticated) return false

      try {
        const newFavorite = await favoritesApi.add(etfCode)
        setFavorites((prev) => [newFavorite, ...prev])
        setFavoriteCodes((prev) => new Set(prev).add(etfCode))
        return true
      } catch (err) {
        console.error('Failed to add favorite:', err)
        return false
      }
    },
    [isAuthenticated]
  )

  const removeFavorite = useCallback(
    async (etfCode: string): Promise<boolean> => {
      if (!isAuthenticated) return false

      try {
        await favoritesApi.remove(etfCode)
        setFavorites((prev) => prev.filter((f) => f.etf_code !== etfCode))
        setFavoriteCodes((prev) => {
          const newSet = new Set(prev)
          newSet.delete(etfCode)
          return newSet
        })
        return true
      } catch (err) {
        console.error('Failed to remove favorite:', err)
        return false
      }
    },
    [isAuthenticated]
  )

  const toggleFavorite = useCallback(
    async (etfCode: string): Promise<boolean> => {
      if (favoriteCodes.has(etfCode)) {
        return removeFavorite(etfCode)
      } else {
        return addFavorite(etfCode)
      }
    },
    [favoriteCodes, addFavorite, removeFavorite]
  )

  const isFavorite = useCallback(
    (etfCode: string): boolean => {
      return favoriteCodes.has(etfCode)
    },
    [favoriteCodes]
  )

  return {
    favorites,
    favoriteCodes,
    isLoading,
    error,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    refresh: fetchFavorites,
  }
}

export default useFavorites
