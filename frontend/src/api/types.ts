/** API type definitions */

export interface Category {
  id: number
  name: string
  description: string | null
  sort_order: number
}

export interface Tag {
  id: number
  name: string
  color: string
}

export interface ETFSummary {
  code: string
  name: string
  category: string | null
  expense_ratio: number | null
  dividend_yield: number | null
  market_price: number | null
  tags: Tag[]
}

export interface ETFDetail {
  code: string
  name: string
  description: string | null
  category_id: number | null
  category: Category | null
  expense_ratio: number | null
  dividend_yield: number | null
  nav: number | null
  market_price: number | null
  deviation_rate: number | null
  total_assets: number | null
  listing_date: string | null
  tags: Tag[]
}

export interface ChartDataPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChartData {
  code: string
  name: string
  period: string
  data: ChartDataPoint[]
}

export interface Perspective {
  id: string
  name: string
  description: string
}

export interface Recommendation {
  perspective: Perspective
  items: ETFSummary[]
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
  meta?: {
    total: number
    limit: number
    offset: number
  }
}

export interface ApiError {
  success: false
  error: {
    message: string
    code: number
    details?: Array<{ field: string; message: string }>
  }
}

export type ChartPeriod =
  | '1m'
  | '3m'
  | '6m'
  | '1y'
  | '3y'
  | '5y'
  | '10y'
  | '20y'

export interface User {
  id: number
  email: string
  username: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  last_login_at?: string
}

export interface LoginRequest {
  email: string
  password: string
  remember?: boolean
}

export interface RegisterRequest {
  email: string
  password: string
  username: string
}

export interface Favorite {
  id: number
  etf_code: string
  created_at: string
  etf: ETFSummary
}

export interface Trade {
  id: number
  user_id: number
  etf_code: string
  trade_type: 'buy' | 'sell'
  quantity: number
  price: number
  trade_date: string
  memo: string | null
  total_amount: number
  created_at: string
  updated_at: string
  etf?: ETFSummary
}

export interface CreateTradeRequest {
  etf_code: string
  trade_type: 'buy' | 'sell'
  quantity: number
  price: number
  trade_date: string
  memo?: string
}

export interface UpdateTradeRequest {
  trade_type?: 'buy' | 'sell'
  quantity?: number
  price?: number
  trade_date?: string
  memo?: string
}

export interface TradeFilterOptions {
  startDate?: string // YYYY-MM-DD
  endDate?: string // YYYY-MM-DD
  search?: string // ETFコードまたは名前で検索
}

export interface Holding {
  etf_code: string
  etf: ETFSummary | null
  quantity: number
  average_cost: number
  total_cost: number
  current_price: number
  current_value: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
}

export interface PortfolioSummary {
  total_value: number
  total_cost: number
  total_unrealized_pnl: number
  total_unrealized_pnl_percent: number
  holdings_count: number
}

export type ValuationHistoryPeriod = '1m' | '3m' | '6m' | '1y' | '3y' | '5y' | '10y' | '20y'

export interface ValuationDataPoint {
  date: string
  value: number
}

export type ValuationHistory = ValuationDataPoint[]

export interface ETFPerformance {
  code: string
  returns: {
    '1m': number | null
    '3m': number | null
    '6m': number | null
    '1y': number | null
  }
  volatility: number | null
}

export interface PerformanceComparison {
  items: ETFPerformance[]
  periods: string[]
}

export type PerformancePeriod =
  | '1m'
  | '3m'
  | '6m'
  | '1y'
  | '3y'
  | '5y'
  | '10y'
  | '20y'

export type PerformanceReturns = Partial<
  Record<PerformancePeriod, number | null>
>

export interface BatchPerformanceItem {
  returns: PerformanceReturns
  regression: PerformanceReturns
}

export type BatchPerformanceData = Record<string, BatchPerformanceItem>

export interface ETFWithPerformance extends ETFSummary {
  performance?: PerformanceReturns
}

/** Batch chart API types */

/** Single ETF, multiple periods response */
export interface BatchPeriodsChartData {
  code: string
  name: string
  charts: Partial<Record<ChartPeriod, ChartDataPoint[]>>
}

/** Multiple ETFs, single period response */
export type BatchCodesChartData = Record<string, ChartData>
