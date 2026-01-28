/** Chart utility functions */
import { ChartDataPoint, ChartPeriod } from '../api'
import { EXPECTED_TRADING_DAYS, DATA_SUFFICIENCY_THRESHOLD } from './constants'

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

export interface RegressionLineResult {
  startY: number
  endY: number
}

/**
 * Calculate linear regression line using least squares method
 * Returns start and end Y values for the regression line
 * Formula: y = ax + b where a = slope, b = intercept
 */
export function calculateRegressionLine(
  data: { date: string; close: number }[]
): RegressionLineResult | null {
  const n = data.length
  if (n < 2) return null

  // Use index as x value (0, 1, 2, ...)
  const prices = data.map((d) => d.close)

  // Calculate sums for least squares
  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0

  for (let i = 0; i < n; i++) {
    sumX += i
    sumY += prices[i]
    sumXY += i * prices[i]
    sumXX += i * i
  }

  // Calculate slope (a) and intercept (b)
  const denominator = n * sumXX - sumX * sumX
  if (denominator === 0) return null

  const slope = (n * sumXY - sumX * sumY) / denominator
  const intercept = (sumY - slope * sumX) / n

  // Calculate Y values at start (x=0) and end (x=n-1)
  const startY = intercept
  const endY = slope * (n - 1) + intercept

  return { startY, endY }
}

/**
 * Calculate linear regression line for normalized (percent change) data
 * Returns start and end Y values for the regression line
 */
export function calculateNormalizedRegressionLine(
  data: NormalizedDataPoint[]
): RegressionLineResult | null {
  const n = data.length
  if (n < 2) return null

  const values = data.map((d) => d.percentChange)

  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0

  for (let i = 0; i < n; i++) {
    sumX += i
    sumY += values[i]
    sumXY += i * values[i]
    sumXX += i * i
  }

  const denominator = n * sumXX - sumX * sumX
  if (denominator === 0) return null

  const slope = (n * sumXY - sumX * sumY) / denominator
  const intercept = (sumY - slope * sumX) / n

  const startY = intercept
  const endY = slope * (n - 1) + intercept

  return { startY, endY }
}

export interface DataSufficiencyResult {
  isSufficient: boolean
  actualDays: number
  expectedDays: number
  ratio: number
  actualPeriodLabel: string
}

/**
 * Check if data is sufficient for the given chart period
 * Returns detailed information about data sufficiency
 */
export function checkDataSufficiency(
  period: ChartPeriod,
  dataLength: number,
  threshold: number = DATA_SUFFICIENCY_THRESHOLD
): DataSufficiencyResult {
  const expectedDays = EXPECTED_TRADING_DAYS[period] ?? 240
  const ratio = dataLength / expectedDays
  const isSufficient = ratio >= threshold

  return {
    isSufficient,
    actualDays: dataLength,
    expectedDays,
    ratio,
    actualPeriodLabel: getActualPeriodLabel(dataLength),
  }
}

/**
 * Convert data length to human-readable period label
 */
function getActualPeriodLabel(days: number): string {
  if (days >= 2400) {
    const years = Math.floor(days / 240)
    return `${years}年分`
  }
  if (days >= 240) {
    const years = Math.floor(days / 240)
    return `${years}年分`
  }
  if (days >= 60) {
    const months = Math.floor(days / 20)
    return `${months}ヶ月分`
  }
  if (days >= 20) {
    const weeks = Math.floor(days / 5)
    return `${weeks}週間分`
  }
  return `${days}日分`
}
