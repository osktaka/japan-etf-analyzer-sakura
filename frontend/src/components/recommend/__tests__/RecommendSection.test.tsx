/** RecommendSection component tests */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RecommendSection } from '../RecommendSection'
import * as api from '../../../api'
import * as hooks from '../../../hooks'

vi.mock('../../../api', () => ({
  getPerspectives: vi.fn(),
}))

vi.mock('../../../hooks', () => ({
  useRecommendations: vi.fn(),
}))

const mockPerspectives = [
  { id: 'popular', name: '人気', description: '人気のETF' },
  { id: 'dividend', name: '高配当', description: '配当利回りが高いETF' },
]

const mockRecommendation = {
  perspective: { id: 'popular', name: '人気', description: '人気のETFを表示' },
  items: [
    {
      code: '1306',
      name: 'TOPIX ETF',
      category: '国内株式',
      expense_ratio: 0.1,
      dividend_yield: 2.0,
      market_price: 2000,
      tags: [],
    },
  ],
}

describe('RecommendSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPerspectives).mockResolvedValue(mockPerspectives)
    vi.mocked(hooks.useRecommendations).mockReturnValue({
      data: mockRecommendation,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  it('セクションタイトルが表示される', async () => {
    render(<RecommendSection onETFClick={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('おすすめ銘柄')).toBeInTheDocument()
    })
  })

  it('観点タブが表示される', async () => {
    render(<RecommendSection onETFClick={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('人気')).toBeInTheDocument()
      expect(screen.getByText('高配当')).toBeInTheDocument()
    })
  })

  it('おすすめETFが表示される', async () => {
    render(<RecommendSection onETFClick={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('1306')).toBeInTheDocument()
      expect(screen.getByText('TOPIX ETF')).toBeInTheDocument()
    })
  })

  it('観点の説明が表示される', async () => {
    render(<RecommendSection onETFClick={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('人気のETFを表示')).toBeInTheDocument()
    })
  })

  it('ローディング中はローディング表示', async () => {
    vi.mocked(hooks.useRecommendations).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    })

    render(<RecommendSection onETFClick={vi.fn()} />)

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('エラー時はエラーメッセージ表示', async () => {
    vi.mocked(hooks.useRecommendations).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('API Error'),
      refetch: vi.fn(),
    })

    render(<RecommendSection onETFClick={vi.fn()} />)

    expect(screen.getByText('データの取得に失敗しました')).toBeInTheDocument()
  })

  it('ETFカードクリック時にonETFClickが呼ばれる', async () => {
    const handleClick = vi.fn()
    render(<RecommendSection onETFClick={handleClick} />)

    await waitFor(() => {
      expect(screen.getByText('1306')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('TOPIX ETF').closest('[role="button"]')!)
    expect(handleClick).toHaveBeenCalledWith('1306')
  })

  it('比較トグルコールバックが渡される', async () => {
    const handleCompare = vi.fn()
    render(
      <RecommendSection
        onETFClick={vi.fn()}
        isInCompare={() => false}
        onCompareToggle={handleCompare}
      />
    )

    await waitFor(() => {
      expect(screen.getByLabelText('比較に追加')).toBeInTheDocument()
    })
  })

  it('お気に入りコールバックが渡される', async () => {
    const handleFavorite = vi.fn()
    render(
      <RecommendSection
        onETFClick={vi.fn()}
        isFavorite={() => false}
        onFavoriteToggle={handleFavorite}
      />
    )

    await waitFor(() => {
      expect(screen.getByLabelText('お気に入りに追加')).toBeInTheDocument()
    })
  })
})
