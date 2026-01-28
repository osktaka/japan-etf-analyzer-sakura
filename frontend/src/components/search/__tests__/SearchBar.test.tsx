/** SearchBar component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SearchBar } from '../SearchBar'

describe('SearchBar', () => {
  it('検索ボックスが表示される', () => {
    render(<SearchBar onSearch={vi.fn()} />)
    expect(screen.getByPlaceholderText('銘柄を検索...')).toBeInTheDocument()
  })

  it('カスタムプレースホルダーが表示される', () => {
    render(<SearchBar onSearch={vi.fn()} placeholder="銘柄コードで検索" />)
    expect(screen.getByPlaceholderText('銘柄コードで検索')).toBeInTheDocument()
  })

  it('検索ボタンが表示される', () => {
    render(<SearchBar onSearch={vi.fn()} />)
    expect(screen.getByRole('button', { name: '検索' })).toBeInTheDocument()
  })

  it('入力値が変更される', () => {
    render(<SearchBar onSearch={vi.fn()} />)
    const input = screen.getByPlaceholderText('銘柄を検索...')

    fireEvent.change(input, { target: { value: 'TOPIX' } })
    expect(input).toHaveValue('TOPIX')
  })

  it('フォーム送信時にonSearchが呼ばれる', () => {
    const handleSearch = vi.fn()
    render(<SearchBar onSearch={handleSearch} />)

    const input = screen.getByPlaceholderText('銘柄を検索...')
    fireEvent.change(input, { target: { value: 'TOPIX' } })
    fireEvent.submit(
      screen.getByRole('button', { name: '検索' }).closest('form')!
    )

    expect(handleSearch).toHaveBeenCalledWith('TOPIX')
  })

  it('空の値でも検索が実行される', () => {
    const handleSearch = vi.fn()
    render(<SearchBar onSearch={handleSearch} />)

    fireEvent.submit(
      screen.getByRole('button', { name: '検索' }).closest('form')!
    )
    expect(handleSearch).toHaveBeenCalledWith('')
  })
})
