/** Context for managing compare list with sessionStorage */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  ReactNode,
} from 'react'
import { MAX_COMPARE_ITEMS, MAX_COMPARE_ITEMS_LOGGED_IN } from '../utils'
import { useAuth } from './useAuth'

interface CompareContextType {
  codes: string[]
  count: number
  addCode: (code: string) => void
  removeCode: (code: string) => void
  toggleCode: (code: string) => void
  clearAll: () => void
  isInList: (code: string) => boolean
  canAdd: boolean
  maxItems: number
}

const CompareContext = createContext<CompareContextType | null>(null)

const STORAGE_KEY = 'etf-compare-list'

export function CompareProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const maxItems = isAuthenticated
    ? MAX_COMPARE_ITEMS_LOGGED_IN
    : MAX_COMPARE_ITEMS

  const [codes, setCodes] = useState<string[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(codes))
  }, [codes])

  const addCode = useCallback(
    (code: string) => {
      setCodes((prev) => {
        if (prev.includes(code) || prev.length >= maxItems) return prev
        return [...prev, code]
      })
    },
    [maxItems]
  )

  const removeCode = useCallback((code: string) => {
    setCodes((prev) => prev.filter((c) => c !== code))
  }, [])

  const toggleCode = useCallback(
    (code: string) => {
      setCodes((prev) => {
        if (prev.includes(code)) {
          return prev.filter((c) => c !== code)
        }
        if (prev.length >= maxItems) return prev
        return [...prev, code]
      })
    },
    [maxItems]
  )

  const clearAll = useCallback(() => {
    setCodes([])
  }, [])

  const isInList = useCallback((code: string) => codes.includes(code), [codes])

  const value: CompareContextType = {
    codes,
    count: codes.length,
    addCode,
    removeCode,
    toggleCode,
    clearAll,
    isInList,
    canAdd: codes.length < maxItems,
    maxItems,
  }

  return (
    <CompareContext.Provider value={value}>{children}</CompareContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCompareList() {
  const context = useContext(CompareContext)
  if (!context) {
    throw new Error('useCompareList must be used within CompareProvider')
  }
  return context
}
