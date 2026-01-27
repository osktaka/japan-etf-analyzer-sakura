/** ETFCard component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ETFCard } from '../ETFCard'
import { ETFSummary } from '../../../api'

const mockETF: ETFSummary = {
  code: '1306',
  name: 'NEXT FUNDS TOPIX連動型上場投信',
  category: '国内株式',
  expense_ratio: 0.088,
  dividend_yield: 2.15,
  market_price: 2345,
  tags: [{ id: 1, name: 'TOPIX連動', color: '#3B82F6' }],
}

describe('ETFCard', () => {
  it('ETFコードが表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(screen.getByText('1306')).toBeInTheDocument()
  })

  it('ETF名が表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(
      screen.getByText('NEXT FUNDS TOPIX連動型上場投信')
    ).toBeInTheDocument()
  })

  it('カテゴリが表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(screen.getByText('国内株式')).toBeInTheDocument()
  })

  it('タグが表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
  })

  it('配当利回りが表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(screen.getByText('2.15%')).toBeInTheDocument()
  })

  it('信託報酬が表示される', () => {
    render(<ETFCard etf={mockETF} />)
    expect(screen.getByText('0.09%')).toBeInTheDocument()
  })

  it('クリック時にonClickが呼ばれる', () => {
    const handleClick = vi.fn()
    render(<ETFCard etf={mockETF} onClick={handleClick} />)

    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalled()
  })

  it('Enterキーでクリックイベントが発火する', () => {
    const handleClick = vi.fn()
    render(<ETFCard etf={mockETF} onClick={handleClick} />)

    fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' })
    expect(handleClick).toHaveBeenCalled()
  })

  it('比較チェックボックスが表示される（showCompareButton=true）', () => {
    render(
      <ETFCard etf={mockETF} showCompareButton onCompareToggle={vi.fn()} />
    )
    expect(screen.getByLabelText('比較に追加')).toBeInTheDocument()
  })

  it('選択状態でaria-labelが変わる', () => {
    render(
      <ETFCard
        etf={mockETF}
        showCompareButton
        isSelected
        onCompareToggle={vi.fn()}
      />
    )
    expect(screen.getByLabelText('比較から外す')).toBeInTheDocument()
  })

  it('比較チェックボックスクリック時にonCompareToggleが呼ばれる', () => {
    const handleToggle = vi.fn()
    render(
      <ETFCard etf={mockETF} showCompareButton onCompareToggle={handleToggle} />
    )

    fireEvent.click(screen.getByLabelText('比較に追加'))
    expect(handleToggle).toHaveBeenCalled()
  })

  it('カテゴリがnullの場合は表示されない', () => {
    const etfNoCategory = { ...mockETF, category: null }
    render(<ETFCard etf={etfNoCategory} />)
    expect(screen.queryByText('国内株式')).not.toBeInTheDocument()
  })

  it('タグが空の場合はタグエリアが表示されない', () => {
    const etfNoTags = { ...mockETF, tags: [] }
    render(<ETFCard etf={etfNoTags} />)
    expect(screen.queryByText('TOPIX連動')).not.toBeInTheDocument()
  })
})
