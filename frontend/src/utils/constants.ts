/** Application constants */

export const CHART_PERIODS = [
  { id: '1m', label: '1M' },
  { id: '3m', label: '3M' },
  { id: '6m', label: '6M' },
  { id: '1y', label: '1Y' },
  { id: '3y', label: '3Y' },
  { id: '5y', label: '5Y' },
  { id: '10y', label: '10Y' },
  { id: '20y', label: '20Y' },
] as const

export const MAX_COMPARE_ITEMS = 5
export const MAX_COMPARE_ITEMS_LOGGED_IN = 10

export const PERSPECTIVE_COLORS: Record<string, string> = {
  dividend: '#10B981', // 配当収入: Emerald
  'low-cost': '#3B82F6', // 低コスト: Blue
  stability: '#06B6D4', // 安定性: Cyan
  volume: '#F97316', // 取引規模: Orange
  growth: '#8B5CF6', // 成長性: Violet
  balance: '#6366F1', // バランス: Indigo
  custom: '#EC4899', // カスタム: Pink
}

export const PERSPECTIVE_GRADIENTS: Record<string, string> = {
  dividend: 'linear-gradient(135deg, #10B981, #059669)',
  'low-cost': 'linear-gradient(135deg, #3B82F6, #1D4ED8)',
  stability: 'linear-gradient(135deg, #06B6D4, #0891B2)',
  volume: 'linear-gradient(135deg, #F97316, #C2410C)',
  growth: 'linear-gradient(135deg, #8B5CF6, #6D28D9)',
  balance: 'linear-gradient(135deg, #6366F1, #4F46E5)',
  custom: 'linear-gradient(135deg, #EC4899, #BE185D)',
}

export const ROUTES = {
  HOME: '/',
  COMPARE: '/compare',
  LOGIN: '/login',
  REGISTER: '/register',
  MYPAGE: '/mypage',
  PORTFOLIO: '/portfolio',
  ADMIN: '/admin',
  GUIDE: '/guide',
  GUIDE_SEARCH: '/guide/search',
  GUIDE_RECOMMEND: '/guide/recommend',
  GUIDE_COMPARE: '/guide/compare',
  GUIDE_MYPAGE: '/guide/mypage',
  GUIDE_FAQ: '/guide/faq',
  GUIDE_TAGS: '/guide/tags',
  GUIDE_MOMENTUM: '/guide/momentum',
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
