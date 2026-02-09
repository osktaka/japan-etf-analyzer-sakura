/** 売買取引のポップオーバーコンポーネント */
import { useEffect, useRef } from 'react'
import { Trade } from '../../api/types'
import { formatPrice } from '../../utils'
import styles from './TradePopover.module.css'

interface TradePopoverProps {
  trades: Trade[]
  date: string
  position: { x: number; y: number }
  onClose: () => void
}

export function TradePopover({
  trades,
  date,
  position,
  onClose,
}: TradePopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null)

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
      className={styles.overlay}
      style={{ left: position.x, top: position.y }}
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
