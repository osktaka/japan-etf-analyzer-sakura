/** ETF incremental search input for compare page */
import { useState, useEffect, useRef, useCallback } from 'react'

import { searchETFs } from '../../api'
import { ETFSummary } from '../../api/types'
import { useDebounce } from '../../hooks'
import styles from './ETFSearchInput.module.css'

interface ETFSearchInputProps {
  onSelect: (code: string) => void
  existingCodes: string[]
  canAdd: boolean
  maxItems: number
}

export function ETFSearchInput({
  onSelect,
  existingCodes,
  canAdd,
  maxItems,
}: ETFSearchInputProps) {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState<ETFSummary[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const debouncedKeyword = useDebounce(keyword, 300)

  // デバウンス後の検索実行
  useEffect(() => {
    if (!debouncedKeyword.trim()) {
      setResults([])
      setIsOpen(false)
      return
    }

    let cancelled = false
    const fetchResults = async () => {
      try {
        const { items } = await searchETFs({
          keyword: debouncedKeyword,
          limit: 10,
        })
        if (!cancelled) {
          setResults(items)
          setIsOpen(true)
        }
      } catch {
        // API失敗時は無視（再入力で再試行される）
      }
    }
    fetchResults()
    return () => {
      cancelled = true
    }
  }, [debouncedKeyword])

  // 外部クリックでドロップダウン閉じる
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Escキーでドロップダウン閉じる
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
    }
  }, [])

  // 候補選択
  const handleSelect = useCallback(
    (code: string) => {
      onSelect(code)
      setKeyword('')
      setResults([])
      setIsOpen(false)
    },
    [onSelect]
  )

  const placeholder = canAdd
    ? '銘柄コードまたは名称で検索'
    : `上限(${maxItems}件)に達しています`

  return (
    <div className={styles.searchContainer} ref={containerRef}>
      <input
        type="text"
        className={styles.searchInput}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={!canAdd}
      />
      {isOpen && results.length > 0 && (
        <ul className={styles.dropdown}>
          {results.map((etf) => {
            const isExisting = existingCodes.includes(etf.code)
            return (
              <li
                key={etf.code}
                className={`${styles.dropdownItem} ${isExisting ? styles.dropdownItemDisabled : ''}`}
                onClick={() => !isExisting && handleSelect(etf.code)}
              >
                <span className={styles.itemCode}>{etf.code}</span>
                <span className={styles.itemName}>{etf.name}</span>
                {isExisting && <span className={styles.badge}>追加済み</span>}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
