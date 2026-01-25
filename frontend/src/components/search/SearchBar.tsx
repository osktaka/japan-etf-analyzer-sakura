/** Search bar component */
import { useState, FormEvent } from 'react'
import styles from './SearchBar.module.css'

interface SearchBarProps {
  onSearch: (keyword: string) => void
  placeholder?: string
}

export function SearchBar({
  onSearch,
  placeholder = 'ETFを検索...',
}: SearchBarProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(value)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.input}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
      />
      <button type="submit" className={styles.button}>
        検索
      </button>
    </form>
  )
}
