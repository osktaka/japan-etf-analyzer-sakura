/** PriceChart component tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PriceChart } from '../PriceChart'
import { ChartDataPoint } from '../../../api'

// Mock Recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}))

const mockChartData: ChartDataPoint[] = [
  {
    date: '2025-01-01',
    open: 2300,
    high: 2350,
    low: 2290,
    close: 2340,
    volume: 1000000,
  },
  {
    date: '2025-01-02',
    open: 2340,
    high: 2360,
    low: 2330,
    close: 2355,
    volume: 1200000,
  },
  {
    date: '2025-01-03',
    open: 2355,
    high: 2380,
    low: 2350,
    close: 2370,
    volume: 900000,
  },
]

describe('PriceChart', () => {
  it('データがある場合、チャートが表示される', () => {
    render(<PriceChart data={mockChartData} />)

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('空のデータの場合、メッセージが表示される', () => {
    render(<PriceChart data={[]} />)

    expect(screen.getByText('チャートデータがありません')).toBeInTheDocument()
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument()
  })

  it('デフォルトの高さが適用される', () => {
    const { container } = render(<PriceChart data={mockChartData} />)

    const chartContainer = container.firstChild as HTMLElement
    expect(chartContainer).toHaveStyle({ height: '300px' })
  })

  it('カスタム高さが適用される', () => {
    const { container } = render(
      <PriceChart data={mockChartData} height={400} />
    )

    const chartContainer = container.firstChild as HTMLElement
    expect(chartContainer).toHaveStyle({ height: '400px' })
  })

  it('必要なチャート要素が含まれる', () => {
    render(<PriceChart data={mockChartData} />)

    expect(screen.getByTestId('line')).toBeInTheDocument()
    expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })
})
