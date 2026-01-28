/** Application constants */

export const CHART_PERIODS = [
  { id: '1m', label: '1ヶ月' },
  { id: '3m', label: '3ヶ月' },
  { id: '6m', label: '6ヶ月' },
  { id: '1y', label: '1年' },
  { id: '3y', label: '3年' },
  { id: '5y', label: '5年' },
  { id: '10y', label: '10年' },
  { id: '20y', label: '20年' },
] as const

export const MAX_COMPARE_ITEMS = 5

export const PERSPECTIVE_COLORS: Record<string, string> = {
  'high-dividend': '#10B981',
  'low-cost': '#3B82F6',
  beginner: '#14B8A6',
  diversified: '#8B5CF6',
  popular: '#F59E0B',
}

export const ROUTES = {
  HOME: '/',
  COMPARE: '/compare',
  LOGIN: '/login',
  REGISTER: '/register',
  MYPAGE: '/mypage',
  PORTFOLIO: '/portfolio',
  ADMIN: '/admin',
} as const

/** 各期間の期待営業日数（データ充足判定用） */
export const EXPECTED_TRADING_DAYS: Record<string, number> = {
  '1m': 20,
  '3m': 60,
  '6m': 120,
  '1y': 240,
  '3y': 720,
  '5y': 1200,
  '10y': 2400,
  '20y': 4800,
}

/** データ充足率の閾値（この値未満でオーバーレイ表示） */
export const DATA_SUFFICIENCY_THRESHOLD = 0.8
