/** Chart utility functions */
import { ChartDataPoint } from '../api'

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
