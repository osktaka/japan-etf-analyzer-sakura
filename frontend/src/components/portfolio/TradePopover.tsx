/** 売買取引のポップオーバーコンポーネント */
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Trade } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './TradePopover.module.css'

interface TradePopoverProps {
  trades: Trade[]
  date: string
  position: { x: number; y: number; markerY: number }
  onClose: () => void
}

export function TradePopover({
  trades,
  date,
  position,
  onClose,
}: TradePopoverProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [adjustedPos, setAdjustedPos] = useState(position)

  useLayoutEffect(() => {
    const overlay = overlayRef.current
    const popover = popoverRef.current
    const container = overlay?.parentElement
    if (!overlay || !popover || !container) return

    const containerRect = container.getBoundingClientRect()
    const popoverRect = popover.getBoundingClientRect()
    let { x, y } = position

    // 右端はみ出し補正: ポップオーバーの右端がマーカーの左側にくるよう配置
    if (x + popoverRect.width > containerRect.width) {
      x = Math.max(0, position.x - popoverRect.width - 8)
    }
    // 下端はみ出し補正: マーカーの上に表示（マーカーを隠さない）
    if (y + popoverRect.height > containerRect.height) {
      y = Math.max(0, position.markerY - popoverRect.height - 12)
    }

    setAdjustedPos({ x, y, markerY: position.markerY })
  }, [position])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node)
      ) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const formattedDate = new Date(date).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div
      ref={overlayRef}
      className={styles.overlay}
      style={{ left: adjustedPos.x, top: adjustedPos.y }}
    >
      <div ref={popoverRef} className={styles.popover}>
        <div className={styles.dateHeader}>{formattedDate}</div>
        <ul className={styles.tradeList}>
          {trades.map((trade) => (
            <li key={trade.id} className={styles.tradeItem}>
              <span className={styles.etfName}>
                {trade.etf_code} {trade.etf?.name || ''}
              </span>
              <div className={styles.tradeDetail}>
                <span
                  className={
                    trade.trade_type === 'buy'
                      ? styles.typeBuy
                      : styles.typeSell
                  }
                >
                  {trade.trade_type === 'buy' ? '買い' : '売り'}{' '}
                  {trade.quantity}口
                </span>
                <span className={styles.amount}>
                  {formatPrice(trade.total_amount)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default TradePopover
