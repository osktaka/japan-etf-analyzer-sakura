/** TagBadge component tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { TagBadge } from '../TagBadge'
import { Tag } from '../../../api'

const mockTag: Tag = {
  id: 1,
  name: 'TOPIX連動',
  color: '#3B82F6',
  category: 'theme',
  etf_count: 5,
}

describe('TagBadge', () => {
  it('タグ名が表示される', () => {
    render(<TagBadge tag={mockTag} />)
    expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
  })

  it('タグの色が適用される', () => {
    render(<TagBadge tag={mockTag} />)
    const badge = screen.getByText('TOPIX連動')

    expect(badge).toHaveStyle({
      backgroundColor: '#3B82F620',
      color: '#3B82F6',
    })
  })

  it('デフォルトサイズはmd', () => {
    render(<TagBadge tag={mockTag} />)
    const badge = screen.getByText('TOPIX連動')

    expect(badge.className).toContain('md')
  })

  it('size="sm"が適用される', () => {
    render(<TagBadge tag={mockTag} size="sm" />)
    const badge = screen.getByText('TOPIX連動')

    expect(badge.className).toContain('sm')
  })

  it('異なる色のタグが正しく表示される', () => {
    const greenTag: Tag = {
      id: 2,
      name: '高配当',
      color: '#10B981',
      category: 'theme',
      etf_count: 3,
    }
    render(<TagBadge tag={greenTag} />)

    const badge = screen.getByText('高配当')
    expect(badge).toHaveStyle({
      backgroundColor: '#10B98120',
      color: '#10B981',
    })
  })
})
