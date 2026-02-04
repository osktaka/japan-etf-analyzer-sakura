/** CompareTable component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CompareTable } from '../CompareTable'
import { ETFDetail } from '../../../api'

const mockETFs: ETFDetail[] = [
  {
    code: '1306',
    name: 'TOPIX ETF',
    description: null,
    category_id: 1,
    category: { id: 1, name: '国内株式', description: null, sort_order: 1 },
    expense_ratio: 0.088,
    dividend_yield: 2.15,
    nav: 2340,
    market_price: 2345,
    deviation_rate: 0.21,
    total_assets: 150000000000,
    listing_date: '2002-07-13',
    tags: [{ id: 1, name: 'TOPIX連動', color: '#3B82F6', category: 'theme', etf_count: 5 }],
  },
  {
    code: '1321',
    name: 'Nikkei 225 ETF',
    description: null,
    category_id: 1,
    category: { id: 1, name: '国内株式', description: null, sort_order: 1 },
    expense_ratio: 0.1,
    dividend_yield: 1.8,
    nav: 30000,
    market_price: 30100,
    deviation_rate: 0.33,
    total_assets: 200000000000,
    listing_date: '2001-07-09',
    tags: [{ id: 2, name: '日経225連動', color: '#10B981', category: 'theme', etf_count: 3 }],
  },
]

const defaultProps = {
  favoriteCodes: new Set<string>(),
  holdingCodes: new Set<string>(),
  onFavoriteToggle: vi.fn(),
}

describe('CompareTable', () => {
  it('ETFコードと名前が表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('1306')).toBeInTheDocument()
    expect(screen.getByText('TOPIX ETF')).toBeInTheDocument()
    expect(screen.getByText('1321')).toBeInTheDocument()
    expect(screen.getByText('Nikkei 225 ETF')).toBeInTheDocument()
  })

  it('カテゴリが表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getAllByText('国内株式')).toHaveLength(2)
  })

  it('市場価格が表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('￥2,345')).toBeInTheDocument()
    expect(screen.getByText('￥30,100')).toBeInTheDocument()
  })

  it('配当利回りが表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('2.15%')).toBeInTheDocument()
    expect(screen.getByText('1.80%')).toBeInTheDocument()
  })

  it('信託報酬が表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('0.09%')).toBeInTheDocument()
    expect(screen.getByText('0.10%')).toBeInTheDocument()
  })

  it('純資産総額が表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('1500億円')).toBeInTheDocument()
    expect(screen.getByText('2000億円')).toBeInTheDocument()
  })

  it('タグが表示される', () => {
    render(
      <CompareTable etfs={mockETFs} onRemove={vi.fn()} {...defaultProps} />
    )

    expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
    expect(screen.getByText('日経225連動')).toBeInTheDocument()
  })

  it('削除ボタンでonRemoveが呼ばれる', () => {
    const handleRemove = vi.fn()
    render(
      <CompareTable etfs={mockETFs} onRemove={handleRemove} {...defaultProps} />
    )

    fireEvent.click(screen.getByLabelText('1306を削除'))
    expect(handleRemove).toHaveBeenCalledWith('1306')
  })

  it('最良値がハイライトされる（配当利回り：高い方）', () => {
    render(
      <CompareTable
        etfs={mockETFs}
        onRemove={vi.fn()}
        highlightBest
        {...defaultProps}
      />
    )

    const dividendHighlight = screen.getByText('2.15%')
    expect(dividendHighlight.className).toContain('highlight')
  })

  it('最良値がハイライトされる（信託報酬：低い方）', () => {
    render(
      <CompareTable
        etfs={mockETFs}
        onRemove={vi.fn()}
        highlightBest
        {...defaultProps}
      />
    )

    const expenseHighlight = screen.getByText('0.09%')
    expect(expenseHighlight.className).toContain('highlight')
  })

  it('最良値がハイライトされる（純資産総額：高い方）', () => {
    render(
      <CompareTable
        etfs={mockETFs}
        onRemove={vi.fn()}
        highlightBest
        {...defaultProps}
      />
    )

    const assetsHighlight = screen.getByText('2000億円')
    expect(assetsHighlight.className).toContain('highlight')
  })

  it('highlightBest=falseの場合、ハイライトなし', () => {
    render(
      <CompareTable
        etfs={mockETFs}
        onRemove={vi.fn()}
        highlightBest={false}
        {...defaultProps}
      />
    )

    const dividendValue = screen.getByText('2.15%')
    expect(dividendValue.className).not.toContain('highlight')
  })

  it('ETFが1つの場合、ハイライトなし', () => {
    render(
      <CompareTable
        etfs={[mockETFs[0]]}
        onRemove={vi.fn()}
        highlightBest
        {...defaultProps}
      />
    )

    const dividendValue = screen.getByText('2.15%')
    expect(dividendValue.className).not.toContain('highlight')
  })

  it('カテゴリがnullの場合は-が表示される', () => {
    const etfNoCategory = [{ ...mockETFs[0], category: null }]
    render(
      <CompareTable etfs={etfNoCategory} onRemove={vi.fn()} {...defaultProps} />
    )

    const categoryRow = screen.getByText('カテゴリ').closest('tr')
    expect(categoryRow).toHaveTextContent('-')
  })
})
