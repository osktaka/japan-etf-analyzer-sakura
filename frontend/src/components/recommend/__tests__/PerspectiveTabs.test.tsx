/** PerspectiveTabs component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PerspectiveTabs } from '../PerspectiveTabs'
import { Perspective } from '../../../api'

const mockPerspectives: Perspective[] = [
  { id: 'popular', name: '人気', description: '人気のETF' },
  { id: 'dividend', name: '高配当', description: '配当利回りが高いETF' },
  { id: 'low-cost', name: '低コスト', description: '信託報酬が低いETF' },
]

describe('PerspectiveTabs', () => {
  it('すべてのタブが表示される', () => {
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="popular"
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('人気')).toBeInTheDocument()
    expect(screen.getByText('高配当')).toBeInTheDocument()
    expect(screen.getByText('低コスト')).toBeInTheDocument()
  })

  it('タブクリック時にonSelectが呼ばれる', () => {
    const handleSelect = vi.fn()
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="popular"
        onSelect={handleSelect}
      />
    )

    fireEvent.click(screen.getByText('高配当'))
    expect(handleSelect).toHaveBeenCalledWith('dividend')
  })

  it('選択されたタブが強調される', () => {
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="dividend"
        onSelect={vi.fn()}
      />
    )

    const dividendTab = screen.getByText('高配当')
    expect(dividendTab.closest('button')?.className).toContain('active')
  })

  it('空の場合は何も表示されない', () => {
    const { container } = render(
      <PerspectiveTabs
        perspectives={[]}
        selected="popular"
        onSelect={vi.fn()}
      />
    )

    expect(container.querySelector('button')).toBeNull()
  })

  it('各タブがボタンとしてレンダリングされる', () => {
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="popular"
        onSelect={vi.fn()}
      />
    )

    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })
})
