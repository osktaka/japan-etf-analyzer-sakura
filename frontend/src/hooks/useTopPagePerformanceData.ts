/** Hook for managing performance and score data for TopPage */
import { useState, useEffect } from 'react'
import {
  getBatchPerformance,
  getBatchScores,
  BatchPerformanceData,
  BatchScoreData,
} from '../api'
import type { DisplayMode, ScoringMode } from '../components/search'

interface ETFItem {
  code: string
}

interface UseTopPagePerformanceDataParams {
  viewMode: 'card' | 'table'
  displayMode: DisplayMode
  scoringMode: ScoringMode
  items: ETFItem[]
}

interface UseTopPagePerformanceDataResult {
  performance: BatchPerformanceData
  scores: BatchScoreData
}

export function useTopPagePerformanceData({
  viewMode,
  displayMode,
  scoringMode,
  items,
}: UseTopPagePerformanceDataParams): UseTopPagePerformanceDataResult {
  const [performance, setPerformance] = useState<BatchPerformanceData>({})
  const [scores, setScores] = useState<BatchScoreData>({})

  // 表形式表示時にパフォーマンスデータまたはスコアデータを取得
  useEffect(() => {
    if (viewMode === 'table' && items.length > 0) {
      const codes = items.map((item) => item.code)
      getBatchPerformance(codes).then((data) => {
        setPerformance(data)
      })
      if (displayMode === 'score') {
        getBatchScores(codes, scoringMode).then((data) => {
          setScores(data)
        })
      }
    }
  }, [viewMode, items, displayMode, scoringMode])

  return { performance, scores }
}
