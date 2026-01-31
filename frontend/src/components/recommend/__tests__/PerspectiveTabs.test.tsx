/** PerspectiveTabs component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PerspectiveTabs } from '../PerspectiveTabs'
import { Perspective } from '../../../api'

const mockPerspectives: Perspective[] = [
  {
    id: 'dividend',
    name: '配当収入',
    description: '配当利回りが高く、定期的な配当収入を期待できる銘柄',
  },
  {
    id: 'low-cost',
    name: '低コスト',
    description: '信託報酬が低く、長期保有でコストを抑えられる銘柄',
  },
  {
    id: 'balance',
    name: 'バランス',
    description: '複数の観点でバランス良く評価された銘柄',
  },
]

describe('PerspectiveTabs', () => {
  it('すべてのタブが表示される', () => {
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="balance"
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('配当収入')).toBeInTheDocument()
    expect(screen.getByText('低コスト')).toBeInTheDocument()
    expect(screen.getByText('バランス')).toBeInTheDocument()
  })

  it('タブクリック時にonSelectが呼ばれる', () => {
    const handleSelect = vi.fn()
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="balance"
        onSelect={handleSelect}
      />
    )

    fireEvent.click(screen.getByText('配当収入'))
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

    const dividendTab = screen.getByText('配当収入')
    expect(dividendTab.closest('button')?.className).toContain('active')
  })

  it('空の場合は何も表示されない', () => {
    const { container } = render(
      <PerspectiveTabs
        perspectives={[]}
        selected="balance"
        onSelect={vi.fn()}
      />
    )

    expect(container.querySelector('button')).toBeNull()
  })

  it('各タブがボタンとしてレンダリングされる', () => {
    render(
      <PerspectiveTabs
        perspectives={mockPerspectives}
        selected="balance"
        onSelect={vi.fn()}
      />
    )

    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })
})
