/** Chart utility functions */
import { ChartDataPoint, ChartPeriod } from '../api'

export interface NormalizedDataPoint {
  date: string
  percentChange: number
}

/**
 * Normalize chart data to percent change from the first data point
 * First point becomes 0%, subsequent points show change relative to first
 */
export function normalizeToPercentChange(
  data: ChartDataPoint[]
): NormalizedDataPoint[] {
  if (data.length === 0) return []

  const basePrice = data[0].close
  if (basePrice === 0) return []

  return data.map((point) => ({
    date: point.date,
    percentChange: ((point.close - basePrice) / basePrice) * 100,
  }))
}

/** Color palette for overlay chart (8 colors) */
export const CHART_COLORS = [
  '#3B82F6', // blue
  '#EF4444', // red
  '#10B981', // green
  '#F59E0B', // amber
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#84CC16', // lime
] as const

/**
 * Get color for a series by index (cycles if > 8)
 */
export function getChartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length]
}

/** Moving average periods based on chart period */
export function getMovingAveragePeriods(chartPeriod: ChartPeriod): number[] {
  switch (chartPeriod) {
    case '1m':
      return [5]
    case '3m':
      return [5, 25]
    case '6m':
      return [25, 75]
    default:
      // 1y, 3y, 5y, 10y, 20y
      return [25, 75, 200]
  }
}

/** Moving average line colors */
export const MA_COLORS: Record<number, string> = {
  5: '#8B5CF6', // violet
  25: '#F59E0B', // amber
  75: '#10B981', // green
  200: '#EF4444', // red
}

/**
 * Calculate simple moving average for price data
 * Returns null for data points where there isn't enough history
 */
export function calculateMovingAverage(
  data: ChartDataPoint[],
  period: number
): (number | null)[] {
  return data.map((_, index) => {
    if (index < period - 1) return null
    const slice = data.slice(index - period + 1, index + 1)
    const sum = slice.reduce((acc, point) => acc + point.close, 0)
    return sum / period
  })
}
