/** ETFTableView component tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ETFTableView } from '../ETFTableView'
import { BatchScoreData, ETFSummary } from '../../../api/types'

const baseItem: ETFSummary = {
  code: '1306',
  name: 'TOPIX ETF',
  category: '国内株式',
  expense_ratio: 0.088,
  dividend_yield: 2.15,
  market_price: 2345,
  tags: [],
}

const defaultProps = {
  performance: {},
  selectedPeriods: [],
  onETFClick: vi.fn(),
  displayMode: 'score' as const,
  // 評価スコア列のみに絞り込み、判定対象セルを一意にする
  commonColumnVisibility: {
    price: false,
    dividendYield: false,
    expenseRatio: false,
  },
  scoreColumnVisibility: {
    dividendPower: false,
    costEfficiency: false,
    scaleReliability: false,
    tradingQuality: false,
    returnPerformance: false,
  },
  momentumVisible: false,
}

function getRowByCode(code: string): HTMLElement {
  const cell = screen.getByText(code)
  const row = cell.closest('tr')
  if (!row) throw new Error(`row not found for code=${code}`)
  return row
}

describe('ETFTableView - getEvaluationScore', () => {
  it('選択中の切り口(perspective)に対応するスコアが表示される', () => {
    const scores: BatchScoreData = {
      '1306': {
        balance: 75.5,
        dividend: 60,
        'low-cost': 80,
        stability: 70,
        volume: 65,
        growth: 55,
        axis_scores: null,
        score: 70,
      },
    }

    render(
      <ETFTableView
        {...defaultProps}
        items={[baseItem]}
        scores={scores}
        selectedPerspective="balance"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('75.5')
  })

  it('perspectiveを切り替えると対応するスコアに切り替わる', () => {
    const scores: BatchScoreData = {
      '1306': {
        balance: 75.5,
        dividend: 60.2,
        'low-cost': 80,
        stability: 70,
        volume: 65,
        growth: 55,
        axis_scores: null,
        score: 70,
      },
    }

    render(
      <ETFTableView
        {...defaultProps}
        items={[baseItem]}
        scores={scores}
        selectedPerspective="dividend"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('60.2')
  })

  it('該当コードのスコアデータが無い場合は-が表示される', () => {
    render(
      <ETFTableView
        {...defaultProps}
        items={[baseItem]}
        scores={{}}
        selectedPerspective="balance"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('-')
  })

  it('perspectiveがcustomの場合はitemsのscoreを直接使う', () => {
    // getAxisScoreはscores?.[code]が存在する前提でgetEvaluationScoreを呼ぶため、
    // customでもscoresエントリ自体は必要（値そのものは参照されないことを検証する）
    const itemWithScore: ETFSummary = { ...baseItem, score: 88 }
    const scores: BatchScoreData = {
      '1306': {
        balance: 1,
        dividend: 1,
        'low-cost': 1,
        stability: 1,
        volume: 1,
        growth: 1,
        axis_scores: null,
        score: 1,
      },
    }

    render(
      <ETFTableView
        {...defaultProps}
        items={[itemWithScore]}
        scores={scores}
        selectedPerspective="custom"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('88.0')
  })

  it('perspectiveがcustomの場合はscoresに値があってもitemのscoreが優先される', () => {
    const itemWithScore: ETFSummary = { ...baseItem, score: 42 }
    const scores: BatchScoreData = {
      '1306': {
        balance: 75.5,
        dividend: 60.2,
        'low-cost': 80,
        stability: 70,
        volume: 65,
        growth: 55,
        axis_scores: null,
        score: 99,
      },
    }

    render(
      <ETFTableView
        {...defaultProps}
        items={[itemWithScore]}
        scores={scores}
        selectedPerspective="custom"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('42.0')
    expect(getRowByCode('1306')).not.toHaveTextContent('99.0')
  })

  it('複数銘柄でも各コードに対応するスコアがそれぞれ正しく表示される', () => {
    const item2: ETFSummary = {
      ...baseItem,
      code: '1321',
      name: 'Nikkei 225 ETF',
    }
    const scores: BatchScoreData = {
      '1306': {
        balance: 75.5,
        dividend: 60,
        'low-cost': 80,
        stability: 70,
        volume: 65,
        growth: 55,
        axis_scores: null,
        score: 70,
      },
      '1321': {
        balance: 30.1,
        dividend: 20,
        'low-cost': 40,
        stability: 25,
        volume: 35,
        growth: 15,
        axis_scores: null,
        score: 30,
      },
    }

    render(
      <ETFTableView
        {...defaultProps}
        items={[baseItem, item2]}
        scores={scores}
        selectedPerspective="balance"
      />
    )

    expect(getRowByCode('1306')).toHaveTextContent('75.5')
    expect(getRowByCode('1321')).toHaveTextContent('30.1')
  })
})
