/** OverlayChart component tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { OverlayChart } from '../OverlayChart'
import { ChartData, ChartDataPoint } from '../../../api'

// Mock Recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`line-${dataKey}`} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
}))

const mockChartData1: ChartDataPoint[] = [
  {
    date: '2025-01-01',
    open: 1000,
    high: 1050,
    low: 990,
    close: 1000,
    volume: 100000,
  },
  {
    date: '2025-01-02',
    open: 1000,
    high: 1100,
    low: 1000,
    close: 1100,
    volume: 120000,
  },
]

const mockChartData2: ChartDataPoint[] = [
  {
    date: '2025-01-01',
    open: 2000,
    high: 2100,
    low: 1980,
    close: 2000,
    volume: 50000,
  },
  {
    date: '2025-01-02',
    open: 2000,
    high: 2150,
    low: 2000,
    close: 2080,
    volume: 60000,
  },
]

const createDataset = (
  code: string,
  name: string,
  data: ChartDataPoint[]
): { code: string; name: string; data: ChartData } => ({
  code,
  name,
  data: {
    code,
    name,
    period: '1m',
    data,
  },
})

describe('OverlayChart', () => {
  it('複数のデータセットが渡された場合、チャートが表示される', () => {
    const datasets = [
      createDataset('1306', 'TOPIX ETF', mockChartData1),
      createDataset('1321', '日経225 ETF', mockChartData2),
    ]

    render(<OverlayChart datasets={datasets} />)

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('データセットが空の場合、メッセージが表示される', () => {
    render(<OverlayChart datasets={[]} />)

    expect(screen.getByText('チャートデータがありません')).toBeInTheDocument()
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument()
  })

  it('各ETFの線が描画される', () => {
    const datasets = [
      createDataset('1306', 'TOPIX ETF', mockChartData1),
      createDataset('1321', '日経225 ETF', mockChartData2),
    ]

    render(<OverlayChart datasets={datasets} />)

    expect(screen.getByTestId('line-1306')).toBeInTheDocument()
    expect(screen.getByTestId('line-1321')).toBeInTheDocument()
  })

  it('凡例が表示される', () => {
    const datasets = [createDataset('1306', 'TOPIX ETF', mockChartData1)]

    render(<OverlayChart datasets={datasets} />)

    expect(screen.getByTestId('legend')).toBeInTheDocument()
  })

  it('デフォルトの高さが400pxである', () => {
    const datasets = [createDataset('1306', 'TOPIX ETF', mockChartData1)]

    const { container } = render(<OverlayChart datasets={datasets} />)

    const chartContainer = container.firstChild as HTMLElement
    expect(chartContainer).toHaveStyle({ height: '400px' })
  })

  it('カスタム高さが適用される', () => {
    const datasets = [createDataset('1306', 'TOPIX ETF', mockChartData1)]

    const { container } = render(
      <OverlayChart datasets={datasets} height={500} />
    )

    const chartContainer = container.firstChild as HTMLElement
    expect(chartContainer).toHaveStyle({ height: '500px' })
  })

  it('必要なチャート要素が含まれる', () => {
    const datasets = [createDataset('1306', 'TOPIX ETF', mockChartData1)]

    render(<OverlayChart datasets={datasets} />)

    expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })
})
