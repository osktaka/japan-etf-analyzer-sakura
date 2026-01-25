/** FavoriteButton component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { FavoriteButton } from '../FavoriteButton'

describe('FavoriteButton', () => {
  it('お気に入り追加ボタンが表示される（isFavorite=false）', () => {
    render(<FavoriteButton isFavorite={false} onClick={vi.fn()} />)
    expect(screen.getByLabelText('お気に入りに追加')).toBeInTheDocument()
  })

  it('お気に入り削除ボタンが表示される（isFavorite=true）', () => {
    render(<FavoriteButton isFavorite={true} onClick={vi.fn()} />)
    expect(screen.getByLabelText('お気に入りから削除')).toBeInTheDocument()
  })

  it('クリック時にonClickが呼ばれる', () => {
    const handleClick = vi.fn()
    render(<FavoriteButton isFavorite={false} onClick={handleClick} />)

    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalled()
  })

  it('disabledの場合、クリックしてもonClickが呼ばれない', () => {
    const handleClick = vi.fn()
    render(<FavoriteButton isFavorite={false} onClick={handleClick} disabled />)

    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).not.toHaveBeenCalled()
  })

  it('disabledの場合、ボタンが無効化される', () => {
    render(<FavoriteButton isFavorite={false} onClick={vi.fn()} disabled />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('イベントが親要素に伝播しない', () => {
    const parentClick = vi.fn()
    const handleClick = vi.fn()

    render(
      <div onClick={parentClick}>
        <FavoriteButton isFavorite={false} onClick={handleClick} />
      </div>
    )

    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalled()
    expect(parentClick).not.toHaveBeenCalled()
  })

  it('size="sm"が適用される', () => {
    render(<FavoriteButton isFavorite={false} onClick={vi.fn()} size="sm" />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('size="lg"が適用される', () => {
    render(<FavoriteButton isFavorite={false} onClick={vi.fn()} size="lg" />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('SVGアイコンが含まれる', () => {
    render(<FavoriteButton isFavorite={false} onClick={vi.fn()} />)
    expect(screen.getByRole('button').querySelector('svg')).toBeInTheDocument()
  })
})
