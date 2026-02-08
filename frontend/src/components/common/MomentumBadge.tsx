/** Shared momentum badge component */
import { useState } from 'react'
import { getStyleFromLabel } from '../../utils/momentum'
import { MomentumHistoryModal } from '../modal/MomentumHistoryModal'

interface MomentumBadgeProps {
  label: string | null | undefined
  size?: 'sm' | 'md'
  code?: string
}

export function MomentumBadge({ label, size = 'sm', code }: MomentumBadgeProps) {
  const [showHistory, setShowHistory] = useState(false)
  const style = getStyleFromLabel(label)
  if (!style || !label) return null

  const fontSize = size === 'sm' ? '0.7rem' : '0.75rem'
  const padding = size === 'sm' ? '1px 6px' : '2px 8px'
  const isClickable = !!code

  const handleClick = (e: React.MouseEvent) => {
    if (!isClickable) return
    e.stopPropagation()
    setShowHistory(true)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isClickable) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      e.stopPropagation()
      setShowHistory(true)
    }
  }

  return (
    <>
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
          cursor: isClickable ? 'pointer' : undefined,
        }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        title={isClickable ? '勢い履歴を表示' : undefined}
      >
        {label}
      </span>
      {showHistory && code && (
        <MomentumHistoryModal
          code={code}
          onClose={() => setShowHistory(false)}
        />
      )}
    </>
  )
}
