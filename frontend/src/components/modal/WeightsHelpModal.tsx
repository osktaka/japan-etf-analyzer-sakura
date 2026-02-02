/** Weights help modal component */
import { CustomWeights } from '../../api'
import styles from './WeightsHelpModal.module.css'

interface WeightsHelpModalProps {
  isOpen: boolean
  onClose: () => void
  isAuthenticated?: boolean
  customWeights?: CustomWeights | null
  onEditCustom?: () => void
}

export function WeightsHelpModal({
  isOpen,
  onClose,
  isAuthenticated = false,
  customWeights = null,
  onEditCustom,
}: WeightsHelpModalProps) {
  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          &times;
        </button>
        <div className={styles.content}>
          <h2 className={styles.title}>おすすめ銘柄の選び方</h2>
          <p className={styles.description}>
            切り口ごとに評価の重みづけが異なります。
          </p>
          <table className={styles.helpTable}>
            <thead>
              <tr>
                <th>切り口</th>
                <th>配当</th>
                <th>コスト</th>
                <th>安定</th>
                <th>規模</th>
                <th>リターン</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>バランス</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
                <td>20</td>
              </tr>
              <tr>
                <td>配当収入</td>
                <td className={styles.highlight}>50</td>
                <td>10</td>
                <td>20</td>
                <td>10</td>
                <td>10</td>
              </tr>
              <tr>
                <td>低コスト</td>
                <td>10</td>
                <td className={styles.highlight}>50</td>
                <td>20</td>
                <td>10</td>
                <td>10</td>
              </tr>
              <tr>
                <td>安定性</td>
                <td>10</td>
                <td>20</td>
                <td className={styles.highlight}>40</td>
                <td>20</td>
                <td>10</td>
              </tr>
              <tr>
                <td>取引規模</td>
                <td>10</td>
                <td>10</td>
                <td>20</td>
                <td className={styles.highlight}>50</td>
                <td>10</td>
              </tr>
              <tr>
                <td>成長性</td>
                <td>10</td>
                <td>10</td>
                <td>20</td>
                <td>10</td>
                <td className={styles.highlight}>50</td>
              </tr>
              {isAuthenticated && (
                <tr>
                  <td>カスタム</td>
                  <td>{customWeights?.dividend_power != null ? Math.round(customWeights.dividend_power * 100) : '--'}</td>
                  <td>{customWeights?.cost_efficiency != null ? Math.round(customWeights.cost_efficiency * 100) : '--'}</td>
                  <td>{customWeights?.scale_reliability != null ? Math.round(customWeights.scale_reliability * 100) : '--'}</td>
                  <td>{customWeights?.trading_quality != null ? Math.round(customWeights.trading_quality * 100) : '--'}</td>
                  <td>{customWeights?.return_performance != null ? Math.round(customWeights.return_performance * 100) : '--'}</td>
                </tr>
              )}
            </tbody>
          </table>
          {isAuthenticated && onEditCustom && (
            <div className={styles.editLinkWrapper}>
              <button
                className={styles.editLink}
                onClick={(e) => {
                  e.stopPropagation()
                  onClose()
                  onEditCustom()
                }}
              >
                カスタムを編集
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
