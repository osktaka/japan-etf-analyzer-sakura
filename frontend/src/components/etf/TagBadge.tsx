/** Tag badge component */
import { Tag } from '../../api'
import styles from './TagBadge.module.css'

interface TagBadgeProps {
  tag: Tag
  size?: 'sm' | 'md'
}

/** 色の輝度を計算（0-255、高いほど明るい） */
function getLuminance(hex: string): number {
  const color = hex.replace('#', '')
  const r = parseInt(color.substring(0, 2), 16)
  const g = parseInt(color.substring(2, 4), 16)
  const b = parseInt(color.substring(4, 6), 16)
  return (r * 299 + g * 587 + b * 114) / 1000
}

/** 明るい色の場合のスタイル調整を返す */
function getLightColorStyles(bgColor: string): {
  color: string
  border?: string
} {
  const luminance = getLuminance(bgColor)
  // 輝度が180以上の明るい色は暗いテキストと枠線を使用
  if (luminance > 180) {
    return { color: '#374151', border: '1px solid #e5e7eb' }
  }
  return { color: bgColor }
}

export function TagBadge({ tag, size = 'md' }: TagBadgeProps) {
  const lightStyles = getLightColorStyles(tag.color)

  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{
        backgroundColor: `${tag.color}20`,
        ...lightStyles,
      }}
    >
      {tag.name}
    </span>
  )
}
