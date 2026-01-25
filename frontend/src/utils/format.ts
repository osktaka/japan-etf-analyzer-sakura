/** Formatting utility functions */

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return '-'
  return new Intl.NumberFormat('ja-JP', {
    style: 'currency',
    currency: 'JPY',
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '-'
  return `${value.toFixed(2)}%`
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return '-'
  return new Intl.NumberFormat('ja-JP').format(value)
}

export function formatAssets(value: number | null | undefined): string {
  if (value == null) return '-'
  const oku = value / 100000000
  if (oku >= 10000) {
    return `${(oku / 10000).toFixed(1)}兆円`
  }
  return `${Math.round(oku)}億円`
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
}
