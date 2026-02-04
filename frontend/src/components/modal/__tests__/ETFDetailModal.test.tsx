/** ETFDetailModal component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ETFDetailModal } from '../ETFDetailModal'
import * as hooks from '../../../hooks'

vi.mock('../../../hooks', () => ({
  useETFDetail: vi.fn(),
  usePortfolio: vi.fn(() => ({ holdings: [] })),
}))

vi.mock('../../chart', () => ({
  ChartContainer: () => <div data-testid="chart-container">Chart</div>,
  MultiPeriodChart: () => <div data-testid="chart-container">Chart</div>,
}))

const mockETFDetail = {
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
  tags: [{ id: 1, name: 'TOPIX連動', color: '#3B82F6', category: 'theme', etf_count: 5 }],
}

describe('ETFDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(hooks.useETFDetail).mockReturnValue({
      data: mockETFDetail,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  it('codeがnullの場合は何も表示しない', () => {
    const { container } = render(
      <ETFDetailModal code={null} onClose={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('ETFコードが表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('1306')).toBeInTheDocument()
  })

  it('ETF名が表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(
      screen.getByText('NEXT FUNDS TOPIX連動型上場投信')
    ).toBeInTheDocument()
  })

  it('カテゴリが表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('国内株式')).toBeInTheDocument()
  })

  it('タグが表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
  })

  it('各指標が表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('市場価格')).toBeInTheDocument()
    expect(screen.getByText('基準価額')).toBeInTheDocument()
    expect(screen.getByText('配当利回り')).toBeInTheDocument()
    expect(screen.getByText('信託報酬')).toBeInTheDocument()
    expect(screen.getByText('乖離率')).toBeInTheDocument()
    expect(screen.getByText('純資産総額')).toBeInTheDocument()
  })

  it('閉じるボタンクリックでonCloseが呼ばれる', () => {
    const handleClose = vi.fn()
    render(<ETFDetailModal code="1306" onClose={handleClose} />)

    fireEvent.click(screen.getByText('×'))
    expect(handleClose).toHaveBeenCalled()
  })

  it('オーバーレイクリックでonCloseが呼ばれる', () => {
    const handleClose = vi.fn()
    const { container } = render(
      <ETFDetailModal code="1306" onClose={handleClose} />
    )

    const overlay = container.firstChild as HTMLElement
    fireEvent.click(overlay)
    expect(handleClose).toHaveBeenCalled()
  })

  it('モーダル内クリックではonCloseが呼ばれない', () => {
    const handleClose = vi.fn()
    render(<ETFDetailModal code="1306" onClose={handleClose} />)

    fireEvent.click(screen.getByText('NEXT FUNDS TOPIX連動型上場投信'))
    expect(handleClose).not.toHaveBeenCalled()
  })

  it('ローディング中はローディング表示', () => {
    vi.mocked(hooks.useETFDetail).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    })

    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('エラー時はエラーメッセージ表示', () => {
    vi.mocked(hooks.useETFDetail).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('API Error'),
      refetch: vi.fn(),
    })

    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('データの取得に失敗しました')).toBeInTheDocument()
  })

  it('比較チェックボックスが表示される', () => {
    render(
      <ETFDetailModal
        code="1306"
        onClose={vi.fn()}
        isInCompare={false}
        onCompareToggle={vi.fn()}
      />
    )
    expect(screen.getByLabelText('比較に追加')).toBeInTheDocument()
  })

  it('比較チェックボックスクリックでonCompareToggleが呼ばれる', () => {
    const handleToggle = vi.fn()
    render(
      <ETFDetailModal
        code="1306"
        onClose={vi.fn()}
        isInCompare={false}
        onCompareToggle={handleToggle}
      />
    )

    fireEvent.click(screen.getByLabelText('比較に追加'))
    expect(handleToggle).toHaveBeenCalled()
  })

  it('お気に入りボタンが表示される', () => {
    render(
      <ETFDetailModal
        code="1306"
        onClose={vi.fn()}
        isFavorite={false}
        onFavoriteToggle={vi.fn()}
      />
    )
    expect(screen.getByLabelText('お気に入りに追加')).toBeInTheDocument()
  })

  it('チャートコンテナが表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByTestId('chart-container')).toBeInTheDocument()
  })

  it('descriptionが表示される', () => {
    render(<ETFDetailModal code="1306" onClose={vi.fn()} />)
    expect(screen.getByText('TOPIXに連動するETF')).toBeInTheDocument()
  })
})
