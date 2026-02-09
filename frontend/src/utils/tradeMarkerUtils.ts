/** 取引データをチャートデータにマージするユーティリティ */
import { Trade, ValuationDataPoint, ChartDataPoint } from '../api/types'

export interface ChartDataWithTrades extends ValuationDataPoint {
  buyMarker?: number
  sellMarker?: number
  trades?: Trade[]
}

export interface PriceChartDataWithTrades extends ChartDataPoint {
  buyMarker?: number
  sellMarker?: number
  trades?: Trade[]
}

/**
 * 取引データをチャートデータポイントにマージする
 * - 取引日がチャート日付に存在しない場合、次のチャート日付にスナップ
 * - 次の日付がない場合は前の日付にスナップ
 * - チャート期間外の取引は除外
 */
export function mergeTradesWithChartData(
  chartData: ValuationDataPoint[],
  trades: Trade[]
): ChartDataWithTrades[] {
  if (chartData.length === 0 || trades.length === 0) {
    return chartData.map((d) => ({ ...d }))
  }

  const firstDate = chartData[0].date
  const lastDate = chartData[chartData.length - 1].date

  // チャート期間内の取引のみフィルタ
  const filteredTrades = trades.filter(
    (t) => t.trade_date >= firstDate && t.trade_date <= lastDate
  )

  // trade_date でグループ化
  const tradesByDate = new Map<string, Trade[]>()
  for (const trade of filteredTrades) {
    const existing = tradesByDate.get(trade.trade_date)
    if (existing) {
      existing.push(trade)
    } else {
      tradesByDate.set(trade.trade_date, [trade])
    }
  }

  // チャート日付セットを作成
  const chartDateSet = new Set(chartData.map((d) => d.date))

  // 休日スナップ: チャートにない日付の取引を最も近いチャート日付に移動
  const snappedTradesByDate = new Map<string, Trade[]>()
  for (const [tradeDate, dateTrades] of tradesByDate) {
    let targetDate = tradeDate
    if (!chartDateSet.has(tradeDate)) {
      targetDate = findSnapDate(chartData, tradeDate)
    }
    const existing = snappedTradesByDate.get(targetDate)
    if (existing) {
      existing.push(...dateTrades)
    } else {
      snappedTradesByDate.set(targetDate, [...dateTrades])
    }
  }

  // チャートデータにマージ
  return chartData.map((point) => {
    const dayTrades = snappedTradesByDate.get(point.date)
    if (!dayTrades) {
      return { ...point }
    }

    const hasBuy = dayTrades.some((t) => t.trade_type === 'buy')
    const hasSell = dayTrades.some((t) => t.trade_type === 'sell')

    return {
      ...point,
      ...(hasBuy ? { buyMarker: point.value } : {}),
      ...(hasSell ? { sellMarker: point.value } : {}),
      trades: dayTrades,
    }
  })
}

/**
 * 取引日に対応するスナップ先チャート日付を見つける
 * 次のチャート日付を優先、なければ前の日付にスナップ
 */
function findSnapDate(
  chartData: { date: string }[],
  tradeDate: string
): string {
  // 次の日付を探す
  for (const point of chartData) {
    if (point.date >= tradeDate) {
      return point.date
    }
  }
  // 次の日付がない場合、最後の日付にスナップ
  return chartData[chartData.length - 1].date
}

/**
 * 取引データを価格チャートデータポイントにマージする
 * - mergeTradesWithChartData と同じロジックだが、マーカーY座標に close（終値）を使用
 * - 取引日がチャート日付に存在しない場合、次のチャート日付にスナップ
 * - 次の日付がない場合は前の日付にスナップ
 * - チャート期間外の取引は除外
 */
export function mergeTradesWithPriceData(
  chartData: ChartDataPoint[],
  trades: Trade[]
): PriceChartDataWithTrades[] {
  if (chartData.length === 0 || trades.length === 0) {
    return chartData.map((d) => ({ ...d }))
  }

  const firstDate = chartData[0].date
  const lastDate = chartData[chartData.length - 1].date

  // チャート期間内の取引のみフィルタ
  const filteredTrades = trades.filter(
    (t) => t.trade_date >= firstDate && t.trade_date <= lastDate
  )

  // trade_date でグループ化
  const tradesByDate = new Map<string, Trade[]>()
  for (const trade of filteredTrades) {
    const existing = tradesByDate.get(trade.trade_date)
    if (existing) {
      existing.push(trade)
    } else {
      tradesByDate.set(trade.trade_date, [trade])
    }
  }

  // チャート日付セットを作成
  const chartDateSet = new Set(chartData.map((d) => d.date))

  // 休日スナップ: チャートにない日付の取引を最も近いチャート日付に移動
  const snappedTradesByDate = new Map<string, Trade[]>()
  for (const [tradeDate, dateTrades] of tradesByDate) {
    let targetDate = tradeDate
    if (!chartDateSet.has(tradeDate)) {
      targetDate = findSnapDate(chartData, tradeDate)
    }
    const existing = snappedTradesByDate.get(targetDate)
    if (existing) {
      existing.push(...dateTrades)
    } else {
      snappedTradesByDate.set(targetDate, [...dateTrades])
    }
  }

  // チャートデータにマージ
  return chartData.map((point) => {
    const dayTrades = snappedTradesByDate.get(point.date)
    if (!dayTrades) {
      return { ...point }
    }

    const hasBuy = dayTrades.some((t) => t.trade_type === 'buy')
    const hasSell = dayTrades.some((t) => t.trade_type === 'sell')

    return {
      ...point,
      ...(hasBuy ? { buyMarker: point.close } : {}),
      ...(hasSell ? { sellMarker: point.close } : {}),
      trades: dayTrades,
    }
  })
}
