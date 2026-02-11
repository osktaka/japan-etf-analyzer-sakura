/** Momentum history modal component */
import { useState, useEffect } from 'react'
import { getMomentumHistory } from '../../api/etf'
import { MomentumHistoryItem } from '../../api/types'
import { MomentumBadge } from '../common'
import styles from './MomentumHistoryModal.module.css'

interface MomentumHistoryModalProps {
  code: string
  onClose: () => void
}

type RateMode = 'regression' | 'return'

export function MomentumHistoryModal({
  code,
  onClose,
}: MomentumHistoryModalProps) {
  const [data, setData] = useState<MomentumHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [rateMode, setRateMode] = useState<RateMode>('regression')

  useEffect(() => {
    setIsLoading(true)
    getMomentumHistory(code, 250)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setIsLoading(false))
  }, [code])

  const formatRate = (rate: number | null, multiplier: number): string => {
    if (rate === null) return '-'
    const annualized = rate * multiplier
    const sign = annualized >= 0 ? '+' : ''
    return `${sign}${annualized.toFixed(1)}%`
  }

  const getRateClass = (rate: number | null): string => {
    if (rate === null) return ''
    return rate >= 0 ? styles.positive : styles.negative
  }

  const getRate = (
    item: MomentumHistoryItem,
    period: '1m' | '3m' | '6m' | '1y' | '3y' | '5y' | '10y' | '20y'
  ): number | null => {
    const key =
      `${rateMode === 'regression' ? 'regression' : 'return'}_rate_${period}` as keyof MomentumHistoryItem
    return item[key] as number | null
  }

  return (
    <div className={styles.overlay} onClick={(e) => { e.stopPropagation(); onClose() }}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <h3 className={styles.title}>勢い履歴</h3>
        <div className={styles.tabGroup}>
          <button
            className={`${styles.tab} ${rateMode === 'regression' ? styles.tabActive : ''}`}
            onClick={() => setRateMode('regression')}
          >
            回帰上昇率
          </button>
          <button
            className={`${styles.tab} ${rateMode === 'return' ? styles.tabActive : ''}`}
            onClick={() => setRateMode('return')}
          >
            株価上昇率
          </button>
        </div>

        {isLoading && <p className={styles.empty}>読み込み中...</p>}

        {!isLoading && data.length === 0 && (
          <p className={styles.empty}>履歴データがありません</p>
        )}

        {!isLoading && data.length > 0 && (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>日付</th>
                  <th className={styles.th}>勢い</th>
                  <th className={styles.th}>1M</th>
                  <th className={styles.th}>3M</th>
                  <th className={styles.th}>6M</th>
                  <th className={styles.th}>1Y</th>
                  <th className={styles.th}>3Y</th>
                  <th className={styles.th}>5Y</th>
                  <th className={styles.th}>10Y</th>
                  <th className={styles.th}>20Y</th>
                </tr>
              </thead>
              <tbody>
                {data.map((item) => (
                  <tr key={item.date}>
                    <td className={styles.td}>
                      {item.date.replace(/-/g, '/')}
                    </td>
                    <td className={styles.td}>
                      <MomentumBadge label={item.momentum_label} />
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '1m'))}`}
                    >
                      {formatRate(getRate(item, '1m'), 12)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '3m'))}`}
                    >
                      {formatRate(getRate(item, '3m'), 4)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '6m'))}`}
                    >
                      {formatRate(getRate(item, '6m'), 2)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '1y'))}`}
                    >
                      {formatRate(getRate(item, '1y'), 1)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '3y'))}`}
                    >
                      {formatRate(getRate(item, '3y'), 1 / 3)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '5y'))}`}
                    >
                      {formatRate(getRate(item, '5y'), 1 / 5)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '10y'))}`}
                    >
                      {formatRate(getRate(item, '10y'), 1 / 10)}
                    </td>
                    <td
                      className={`${styles.td} ${getRateClass(getRate(item, '20y'))}`}
                    >
                      {formatRate(getRate(item, '20y'), 1 / 20)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
