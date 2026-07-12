/** Generic ETF code autocomplete component */
import { useState, useEffect, useRef, useCallback } from 'react'

import { searchETFs } from '../../api'
import { ETFSummary } from '../../api/types'
import { useDebounce } from '../../hooks'
import styles from './ETFCodeAutocomplete.module.css'

interface ETFCodeAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSelect?: (code: string, name: string, marketPrice?: number | null) => void
  onFocus?: (e: React.FocusEvent<HTMLInputElement>) => void
  disabled?: boolean
  placeholder?: string
  id?: string
  required?: boolean
  className?: string
}

export function ETFCodeAutocomplete({
  value,
  onChange,
  onSelect,
  onFocus,
  disabled,
  placeholder,
  id,
  required,
  className,
}: ETFCodeAutocompleteProps) {
  const [internalKeyword, setInternalKeyword] = useState(value)
  const [results, setResults] = useState<ETFSummary[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const userTyping = useRef(false)
  const debouncedKeyword = useDebounce(internalKeyword, 300)

  // 外部から value が変更された場合に同期（ドロップダウンは開かない）
  useEffect(() => {
    setInternalKeyword(value)
  }, [value])

  // デバウンス後の検索実行
  useEffect(() => {
    if (!userTyping.current) {
      return
    }

    const trimmed = debouncedKeyword.trim()
    if (trimmed.length < 2) {
      setResults([])
      setIsOpen(false)
      setIsLoading(false)
      return
    }

    let cancelled = false
    setIsLoading(true)
    setIsOpen(true)
    const fetchResults = async () => {
      try {
        const { items } = await searchETFs({
          keyword: trimmed,
          limit: 10,
        })
        if (!cancelled) {
          setResults(items)
          setIsOpen(true)
          setHighlightedIndex(-1)
        }
      } catch {
        // API失敗時は無視（再入力で再試行される）
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
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

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      userTyping.current = true
      setInternalKeyword(newValue)
      onChange(newValue)
    },
    [onChange]
  )

  const handleSelect = useCallback(
    (code: string, name: string, marketPrice?: number | null) => {
      userTyping.current = false
      setInternalKeyword(code)
      onChange(code)
      onSelect?.(code, name, marketPrice)
      setIsOpen(false)
      setResults([])
      setHighlightedIndex(-1)
    },
    [onChange, onSelect]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
        return
      }

      if (!isOpen) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlightedIndex((prev) =>
          prev < results.length - 1 ? prev + 1 : 0
        )
        return
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : results.length - 1
        )
        return
      }

      if (e.key === 'Enter' && highlightedIndex >= 0) {
        e.preventDefault()
        const selected = results[highlightedIndex]
        if (selected) {
          handleSelect(selected.code, selected.name, selected.market_price)
        }
      }
    },
    [isOpen, results, highlightedIndex, handleSelect]
  )

  const listboxId = id ? `${id}-listbox` : 'etf-autocomplete-listbox'

  return (
    <div className={styles.container} ref={containerRef}>
      <input
        type="text"
        id={id}
        className={className}
        value={internalKeyword}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={onFocus}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-activedescendant={
          highlightedIndex >= 0
            ? `${listboxId}-option-${highlightedIndex}`
            : undefined
        }
        aria-autocomplete="list"
      />
      {isOpen && (
        <ul id={listboxId} className={styles.dropdown} role="listbox">
          {isLoading ? (
            <li className={styles.message}>検索中...</li>
          ) : results.length === 0 ? (
            <li className={styles.message}>該当する銘柄がありません</li>
          ) : (
            results.map((etf, index) => (
              <li
                key={etf.code}
                id={`${listboxId}-option-${index}`}
                className={`${styles.dropdownItem}${index === highlightedIndex ? ` ${styles.highlighted}` : ''}`}
                role="option"
                aria-selected={index === highlightedIndex}
                onClick={() =>
                  handleSelect(etf.code, etf.name, etf.market_price)
                }
              >
                <span className={styles.itemCode}>{etf.code}</span>
                <span className={styles.itemName}>{etf.name}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
