/** Chart utility function tests */
import { describe, it, expect } from 'vitest'
import {
  normalizeToPercentChange,
  getChartColor,
  CHART_COLORS,
} from '../chartUtils'
import { ChartDataPoint } from '../../api'

const mockChartData: ChartDataPoint[] = [
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
  {
    date: '2025-01-03',
    open: 1100,
    high: 1150,
    low: 1050,
    close: 1050,
    volume: 90000,
  },
]

describe('normalizeToPercentChange', () => {
  it('最初のデータポイントを0%として正規化する', () => {
    const result = normalizeToPercentChange(mockChartData)

    expect(result).toHaveLength(3)
    expect(result[0].percentChange).toBe(0)
    expect(result[0].date).toBe('2025-01-01')
  })

  it('変化率を正しく計算する', () => {
    const result = normalizeToPercentChange(mockChartData)

    // 1000 -> 1100 = +10%
    expect(result[1].percentChange).toBe(10)
    // 1000 -> 1050 = +5%
    expect(result[2].percentChange).toBe(5)
  })

  it('空配列の場合は空配列を返す', () => {
    const result = normalizeToPercentChange([])

    expect(result).toEqual([])
  })

  it('基準価格が0の場合は空配列を返す', () => {
    const dataWithZeroBase: ChartDataPoint[] = [
      {
        date: '2025-01-01',
        open: 0,
        high: 0,
        low: 0,
        close: 0,
        volume: 0,
      },
    ]

    const result = normalizeToPercentChange(dataWithZeroBase)

    expect(result).toEqual([])
  })

  it('負の変化率も正しく計算する', () => {
    const decreasingData: ChartDataPoint[] = [
      {
        date: '2025-01-01',
        open: 1000,
        high: 1000,
        low: 900,
        close: 1000,
        volume: 100000,
      },
      {
        date: '2025-01-02',
        open: 900,
        high: 950,
        low: 850,
        close: 900,
        volume: 100000,
      },
    ]

    const result = normalizeToPercentChange(decreasingData)

    // 1000 -> 900 = -10%
    expect(result[1].percentChange).toBe(-10)
  })
})

describe('getChartColor', () => {
  it('インデックスに対応する色を返す', () => {
    expect(getChartColor(0)).toBe(CHART_COLORS[0])
    expect(getChartColor(1)).toBe(CHART_COLORS[1])
    expect(getChartColor(7)).toBe(CHART_COLORS[7])
  })

  it('8以上のインデックスは循環する', () => {
    expect(getChartColor(8)).toBe(CHART_COLORS[0])
    expect(getChartColor(9)).toBe(CHART_COLORS[1])
    expect(getChartColor(16)).toBe(CHART_COLORS[0])
  })
})

describe('CHART_COLORS', () => {
  it('8色が定義されている', () => {
    expect(CHART_COLORS).toHaveLength(8)
  })

  it('全て有効な色コードである', () => {
    const hexColorPattern = /^#[0-9A-Fa-f]{6}$/
    CHART_COLORS.forEach((color) => {
      expect(color).toMatch(hexColorPattern)
    })
  })
})
