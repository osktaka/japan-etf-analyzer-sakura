/** Shared momentum badge component */
import { getStyleFromLabel } from '../../utils/momentum'

interface MomentumBadgeProps {
  label: string | null | undefined
  size?: 'sm' | 'md'
}

export function MomentumBadge({ label, size = 'sm' }: MomentumBadgeProps) {
  const style = getStyleFromLabel(label)
  if (!style || !label) return null

  const fontSize = size === 'sm' ? '0.7rem' : '0.75rem'
  const padding = size === 'sm' ? '1px 6px' : '2px 8px'

  return (
    <span
      style={{
        display: 'inline-block',
        padding,
        borderRadius: '4px',
        fontSize,
        fontWeight: 500,
        whiteSpace: 'nowrap',
        color: style.color,
        backgroundColor: style.bgColor,
        border: `1px solid ${style.color}`,
        lineHeight: 1.4,
      }}
    >
      {label}
    </span>
  )
}
