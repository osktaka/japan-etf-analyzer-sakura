/** Chart utility function tests */
import { describe, it, expect } from 'vitest'
import {
  normalizeToPercentChange,
  getChartColor,
  calculateRegressionLine,
  calculateYAxisDomain,
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

describe('calculateRegressionLine', () => {
  it('通常データで startY/endY が最小二乗解と一致する', () => {
    // close: 1000, 1100, 1050 → x=0,1,2
    // ΣX=3, ΣY=3150, ΣXY=0*1000+1*1100+2*1050=3200, ΣXX=5, n=3
    // slope = (n*ΣXY - ΣX*ΣY) / (n*ΣXX - ΣX^2)
    //       = (3*3200 - 3*3150) / (3*5 - 9) = 150/6 = 25
    // intercept = (ΣY - slope*ΣX) / n = (3150 - 25*3) / 3 = 1025
    // endY = slope*(n-1) + intercept = 25*2 + 1025 = 1075
    const result = calculateRegressionLine(mockChartData)

    expect(result).not.toBeNull()
    expect(result?.startY).toBeCloseTo(1025, 6)
    expect(result?.endY).toBeCloseTo(1075, 6)
  })

  it('データが2点未満の場合 null を返す', () => {
    expect(calculateRegressionLine([])).toBeNull()
    expect(calculateRegressionLine([mockChartData[0]])).toBeNull()
  })

  it('全価格が同一でも傾き0の回帰線を返す', () => {
    const flatData: ChartDataPoint[] = [
      { date: '2025-01-01', open: 1000, high: 1000, low: 1000, close: 1000, volume: 0 },
      { date: '2025-01-02', open: 1000, high: 1000, low: 1000, close: 1000, volume: 0 },
      { date: '2025-01-03', open: 1000, high: 1000, low: 1000, close: 1000, volume: 0 },
    ]
    const result = calculateRegressionLine(flatData)

    expect(result).not.toBeNull()
    expect(result?.startY).toBeCloseTo(1000, 6)
    expect(result?.endY).toBeCloseTo(1000, 6)
  })
})

describe('calculateYAxisDomain', () => {
  it('通常データで min/max ± 5% パディングを返す', () => {
    // close: 1000, 1100, 1050 / ma25: 1020, 1080
    // 全有限値の min=1000, max=1100
    // range = 1100 - 1000 = 100, pad = 100 * 0.05 = 5
    // domain = [1000 - 5, 1100 + 5] = [995, 1105]
    const points = [
      { close: 1000, ma25: 1020 },
      { close: 1100, ma25: 1080 },
      { close: 1050 },
    ]
    const result = calculateYAxisDomain(points, null)

    expect(result).not.toBeUndefined()
    expect(result?.[0]).toBeCloseTo(995, 6)
    expect(result?.[1]).toBeCloseTo(1105, 6)
  })

  it('回帰線端点が close レンジ外（下振れ）の場合 domain 下限が拡張される', () => {
    // close min=1000, max=1100 / regression startY=900（close 範囲外の下振れ）
    // 走査後 min=900, max=1100
    // range = 1100 - 900 = 200, pad = 200 * 0.05 = 10
    // domain = [900 - 10, 1100 + 10] = [890, 1110]
    const points = [{ close: 1000 }, { close: 1100 }]
    const result = calculateYAxisDomain(points, { startY: 900, endY: 1100 })

    expect(result).not.toBeUndefined()
    expect(result?.[0]).toBeCloseTo(890, 6)
    expect(result?.[1]).toBeCloseTo(1110, 6)
  })

  it('空配列の場合は undefined を返す', () => {
    expect(calculateYAxisDomain([], null)).toBeUndefined()
  })

  it('全 close 同一・regressionLine=null（range=0）は abs(max)*5% パディング', () => {
    // close すべて 1000 → min=max=1000, range=0
    // range>0 が false なので pad = abs(1000) * 0.05 = 50（|| 1 は不発火）
    // domain = [1000 - 50, 1000 + 50] = [950, 1050]
    const points = [{ close: 1000 }, { close: 1000 }, { close: 1000 }]
    const result = calculateYAxisDomain(points, null)

    expect(result).not.toBeUndefined()
    expect(result?.[0]).toBeCloseTo(950, 6)
    expect(result?.[1]).toBeCloseTo(1050, 6)
    // pad = 50 > 0 を確認（domain 幅 = 100）
    expect((result as [number, number])[1] - (result as [number, number])[0]).toBeCloseTo(100, 6)
  })
})
