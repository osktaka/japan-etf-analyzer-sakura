/** API type definitions */

export interface Category {
  id: number;
  name: string;
  description: string | null;
  sort_order: number;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface ETFSummary {
  code: string;
  name: string;
  category: string | null;
  expense_ratio: number | null;
  dividend_yield: number | null;
  market_price: number | null;
  tags: Tag[];
}

export interface ETFDetail {
  code: string;
  name: string;
  description: string | null;
  category_id: number | null;
  category: Category | null;
  expense_ratio: number | null;
  dividend_yield: number | null;
  nav: number | null;
  market_price: number | null;
  deviation_rate: number | null;
  total_assets: number | null;
  listing_date: string | null;
  tags: Tag[];
}

export interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartData {
  code: string;
  name: string;
  period: string;
  data: ChartDataPoint[];
}

export interface Perspective {
  id: string;
  name: string;
  description: string;
}

export interface Recommendation {
  perspective: Perspective;
  items: ETFSummary[];
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  meta?: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface ApiError {
  success: false;
  error: {
    message: string;
    code: number;
    details?: Array<{ field: string; message: string }>;
  };
}

export type ChartPeriod = '1w' | '1m' | '3m' | '6m' | '1y' | '3y';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember?: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
}

export interface Favorite {
  id: number;
  etf_code: string;
  created_at: string;
  etf: ETFSummary;
}
