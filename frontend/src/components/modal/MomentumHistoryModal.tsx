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

export function MomentumHistoryModal({
  code,
  onClose,
}: MomentumHistoryModalProps) {
  const [data, setData] = useState<MomentumHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    getMomentumHistory(code)
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

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <h3 className={styles.title}>勢い履歴</h3>

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
                  <td className={styles.td}>{item.date.replace(/-/g, '/')}</td>
                  <td className={styles.td}>
                    <MomentumBadge label={item.momentum_label} />
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_1m)}`}
                  >
                    {formatRate(item.regression_rate_1m, 12)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_3m)}`}
                  >
                    {formatRate(item.regression_rate_3m, 4)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_6m)}`}
                  >
                    {formatRate(item.regression_rate_6m, 2)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_1y)}`}
                  >
                    {formatRate(item.regression_rate_1y, 1)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_3y)}`}
                  >
                    {formatRate(item.regression_rate_3y, 1 / 3)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_5y)}`}
                  >
                    {formatRate(item.regression_rate_5y, 1 / 5)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_10y)}`}
                  >
                    {formatRate(item.regression_rate_10y, 1 / 10)}
                  </td>
                  <td
                    className={`${styles.td} ${getRateClass(item.regression_rate_20y)}`}
                  >
                    {formatRate(item.regression_rate_20y, 1 / 20)}
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
