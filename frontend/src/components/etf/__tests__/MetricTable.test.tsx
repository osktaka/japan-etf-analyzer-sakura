/** MetricTable component tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MetricTable } from '../MetricTable'
import { ETFDetail } from '../../../api'

const mockETF: ETFDetail = {
  code: '1306',
  name: 'NEXT FUNDS TOPIX連動型上場投信',
  description: 'TOPIXに連動するETF',
  category_id: 1,
  category: { id: 1, name: '国内株式', description: null, sort_order: 1 },
  expense_ratio: 0.088,
  dividend_yield: 2.15,
  nav: 2340,
  market_price: 2345,
  deviation_rate: 0.21,
  total_assets: 150000000000,
  listing_date: '2002-07-13',
  tags: [],
}

describe('MetricTable', () => {
  it('基本指標が表示される', () => {
    render(<MetricTable etf={mockETF} />)

    expect(screen.getByText('市場価格')).toBeInTheDocument()
    expect(screen.getByText('基準価額')).toBeInTheDocument()
    expect(screen.getByText('配当利回り')).toBeInTheDocument()
    expect(screen.getByText('信託報酬')).toBeInTheDocument()
  })

  it('showAll=falseの場合、詳細指標は表示されない', () => {
    render(<MetricTable etf={mockETF} showAll={false} />)

    expect(screen.queryByText('乖離率')).not.toBeInTheDocument()
    expect(screen.queryByText('純資産総額')).not.toBeInTheDocument()
    expect(screen.queryByText('上場日')).not.toBeInTheDocument()
  })

  it('showAll=trueの場合、詳細指標が表示される', () => {
    render(<MetricTable etf={mockETF} showAll />)

    expect(screen.getByText('乖離率')).toBeInTheDocument()
    expect(screen.getByText('純資産総額')).toBeInTheDocument()
    expect(screen.getByText('上場日')).toBeInTheDocument()
  })

  it('配当利回りがハイライトされる', () => {
    render(<MetricTable etf={mockETF} />)

    const dividendValue = screen.getByText('2.15%')
    expect(dividendValue.className).toContain('highlight')
  })

  it('乖離率がプラスの場合、positiveクラスが適用される', () => {
    render(<MetricTable etf={mockETF} showAll />)

    const deviationValue = screen.getByText('0.21%')
    expect(deviationValue.className).toContain('positive')
  })

  it('乖離率がマイナスの場合、negativeクラスが適用される', () => {
    const negativeETF = { ...mockETF, deviation_rate: -0.15 }
    render(<MetricTable etf={negativeETF} showAll />)

    const deviationValue = screen.getByText('-0.15%')
    expect(deviationValue.className).toContain('negative')
  })

  it('compact=trueの場合、compactクラスが適用される', () => {
    const { container } = render(<MetricTable etf={mockETF} compact />)

    const table = container.querySelector('table')
    expect(table?.className).toContain('compact')
  })

  it('nullの値は-で表示される', () => {
    const nullETF = { ...mockETF, market_price: null }
    render(<MetricTable etf={nullETF} />)

    const rows = screen.getAllByRole('row')
    const marketPriceRow = rows.find((row) =>
      row.textContent?.includes('市場価格')
    )
    expect(marketPriceRow).toHaveTextContent('-')
  })

  it('純資産総額が適切にフォーマットされる', () => {
    render(<MetricTable etf={mockETF} showAll />)

    // 150000000000 -> 1500億円
    expect(screen.getByText('1500億円')).toBeInTheDocument()
  })

  it('上場日が適切にフォーマットされる', () => {
    render(<MetricTable etf={mockETF} showAll />)

    expect(screen.getByText('2002年7月13日')).toBeInTheDocument()
  })
})
