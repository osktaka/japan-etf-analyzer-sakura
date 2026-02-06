/** CompareScoreSection component tests */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CompareScoreSection } from '../CompareScoreSection'
import { ETFDetail } from '../../../api'

// Mock API modules
vi.mock('../../../api/compare', () => ({
  getCompareScores: vi.fn(),
}))

vi.mock('../../../api/recommend', () => ({
  getPerspectives: vi.fn(),
}))

import { getCompareScores } from '../../../api/compare'
import { getPerspectives } from '../../../api/recommend'

const mockETFs: ETFDetail[] = [
  {
    code: '1489',
    name: 'NF日経高配当50',
    description: null,
    category_id: 1,
    category: { id: 1, name: '国内株式', description: null, sort_order: 1 },
    expense_ratio: 0.308,
    dividend_yield: 3.5,
    nav: 1500,
    market_price: 1505,
    deviation_rate: 0.33,
    total_assets: 50000000000,
    listing_date: '2017-02-13',
    tags: [],
  },
  {
    code: '1343',
    name: 'NEXT FUNDS東証REIT指数',
    description: null,
    category_id: 2,
    category: { id: 2, name: 'REIT', description: null, sort_order: 2 },
    expense_ratio: 0.155,
    dividend_yield: 4.0,
    nav: 2000,
    market_price: 2010,
    deviation_rate: 0.5,
    total_assets: 80000000000,
    listing_date: '2008-09-18',
    tags: [],
  },
]

const mockScores = {
  '1489': {
    score: 73,
    axis_scores: {
      dividend_power: 80,
      cost_efficiency: 60,
      scale_reliability: 70,
      trading_quality: 55,
      return_performance: 75,
    },
  },
  '1343': {
    score: 64,
    axis_scores: {
      dividend_power: 50,
      cost_efficiency: 90,
      scale_reliability: 65,
      trading_quality: 40,
      return_performance: 60,
    },
  },
}

const mockPerspectives = [
  { id: 'balance', name: 'バランス', description: 'バランス重視' },
  { id: 'dividend', name: '配当', description: '配当重視' },
]

const defaultProps = {
  etfs: mockETFs,
  colCount: 3,
  onHelpClick: vi.fn(),
}

// Helper to render inside a table
function renderInTable(ui: React.ReactNode) {
  return render(
    <table>
      <tbody>{ui}</tbody>
    </table>
  )
}

describe('CompareScoreSection', () => {
  beforeEach(() => {
    vi.mocked(getPerspectives).mockResolvedValue(mockPerspectives)
    vi.mocked(getCompareScores).mockResolvedValue(mockScores)
  })

  it('セクションヘッダー「評価スコア」が表示される', async () => {
    renderInTable(<CompareScoreSection {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('評価スコア')).toBeInTheDocument()
    })
  })

  it('5軸ラベルが表示される', async () => {
    renderInTable(<CompareScoreSection {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('配当力')).toBeInTheDocument()
    })
    expect(screen.getByText('コスト')).toBeInTheDocument()
    expect(screen.getByText('安定')).toBeInTheDocument()
    expect(screen.getByText('規模')).toBeInTheDocument()
    expect(screen.getByText('リターン')).toBeInTheDocument()
  })

  it('総合スコア行が表示される', async () => {
    renderInTable(<CompareScoreSection {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('総合スコア')).toBeInTheDocument()
    })
  })

  it('ローディング中は「...」が表示される', () => {
    // Never resolve to keep loading state
    vi.mocked(getCompareScores).mockReturnValue(new Promise(() => {}))

    renderInTable(<CompareScoreSection {...defaultProps} />)

    const ellipses = screen.getAllByText('...')
    expect(ellipses.length).toBeGreaterThan(0)
  })

  it('スコアデータが取得後に表示される', async () => {
    renderInTable(<CompareScoreSection {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('73点')).toBeInTheDocument()
    })
    expect(screen.getByText('64点')).toBeInTheDocument()
  })

  it('getCompareScoresが正しい引数で呼ばれる', async () => {
    renderInTable(<CompareScoreSection {...defaultProps} />)

    await waitFor(() => {
      expect(getCompareScores).toHaveBeenCalledWith(
        ['1489', '1343'],
        'balance',
        'full',
        undefined
      )
    })
  })
})
