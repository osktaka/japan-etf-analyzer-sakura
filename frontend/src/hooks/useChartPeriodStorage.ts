/** Hook for managing chart period selection in localStorage */
import { useState, useEffect } from 'react'
import type { ChartPeriod } from '../api'

const CHART_PERIODS_STORAGE_KEY = 'etf-chart-periods'
const DEFAULT_CHART_PERIODS: ChartPeriod[] = ['3m', '6m', '1y', '3y', '5y', '10y']

// ローカルストレージからチャート期間を復元
const getStoredChartPeriods = (): ChartPeriod[] => {
  try {
    const stored = localStorage.getItem(CHART_PERIODS_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch {
    // パースエラー時はデフォルト値を返す
  }
  return DEFAULT_CHART_PERIODS
}

// ローカルストレージにチャート期間を保存
const saveChartPeriods = (periods: ChartPeriod[]): void => {
  try {
    localStorage.setItem(CHART_PERIODS_STORAGE_KEY, JSON.stringify(periods))
  } catch {
    // 保存失敗時は無視（ストレージが無効な環境など）
  }
}

export function useChartPeriodStorage() {
  const [chartPeriods, setChartPeriods] = useState<ChartPeriod[]>(
    getStoredChartPeriods
  )

  useEffect(() => {
    saveChartPeriods(chartPeriods)
  }, [chartPeriods])

  return {
    chartPeriods,
    setChartPeriods,
  }
}
