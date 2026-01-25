/** Application constants */

export const CHART_PERIODS = [
  { id: '1w', label: '1週間' },
  { id: '1m', label: '1ヶ月' },
  { id: '3m', label: '3ヶ月' },
  { id: '6m', label: '6ヶ月' },
  { id: '1y', label: '1年' },
  { id: '3y', label: '3年' },
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
} as const
