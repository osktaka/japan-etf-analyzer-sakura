import { useState, useEffect, FormEvent } from 'react'
import { ETFCodeAutocomplete } from '../common'
import styles from './SearchBar.module.css'

interface SearchBarProps {
  onSearch: (keyword: string) => void
  onClear?: () => void
  placeholder?: string
  initialKeyword?: string
}

export function SearchBar({
  onSearch,
  onClear,
  placeholder = '銘柄を検索...',
  initialKeyword = '',
}: SearchBarProps) {
  const [value, setValue] = useState(initialKeyword)

  useEffect(() => {
    setValue(initialKeyword)
  }, [initialKeyword])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(value)
  }

  const handleClear = () => {
    setValue('')
    onClear?.()
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <ETFCodeAutocomplete
        value={value}
        onChange={setValue}
        onSelect={(code) => onSearch(code)}
        onFocus={(e) => e.target.select()}
        className={styles.input}
        placeholder={placeholder}
      />
      <button type="submit" className={styles.button}>
        検索
      </button>
      {onClear && (
        <button
          type="button"
          className={styles.clearButton}
          onClick={handleClear}
        >
          クリア
        </button>
      )}
    </form>
  )
}
