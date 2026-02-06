/** Compare score section component */
import { useState, useEffect } from 'react'
import { getPerspectives } from '../../api/recommend'
import { getCompareScores, CompareScores } from '../../api/compare'
import { Perspective, ETFDetail, CustomWeights } from '../../api/types'
import { PerspectiveTabs } from '../recommend/PerspectiveTabs'
import styles from './CompareScoreSection.module.css'

const AXIS_DEFINITIONS = [
  { key: 'dividend_power', label: '配当力' },
  { key: 'cost_efficiency', label: 'コスト' },
  { key: 'scale_reliability', label: '安定' },
  { key: 'trading_quality', label: '規模' },
  { key: 'return_performance', label: 'リターン' },
] as const

interface CompareScoreSectionProps {
  etfs: ETFDetail[]
  colCount: number
  onHelpClick: () => void
  onCustomClick?: () => void
  customWeights?: CustomWeights | null
}

export function CompareScoreSection({
  etfs,
  colCount,
  onHelpClick,
  onCustomClick,
  customWeights,
}: CompareScoreSectionProps) {
  const [perspectives, setPerspectives] = useState<Perspective[]>([])
  const [selectedPerspective, setSelectedPerspective] = useState(
    () => localStorage.getItem('compare-perspective') || 'balance'
  )
  const [scores, setScores] = useState<CompareScores>({})
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    getPerspectives().then(setPerspectives)
  }, [])

  useEffect(() => {
    if (etfs.length === 0) return

    const codes = etfs.map((etf) => etf.code)
    setIsLoading(true)
    getCompareScores(codes, selectedPerspective, 'full', customWeights)
      .then((data) => {
        setScores(data ?? {})
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [etfs, selectedPerspective, customWeights])

  const handleSelect = (perspective: string) => {
    setSelectedPerspective(perspective)
    localStorage.setItem('compare-perspective', perspective)
  }

  const handleCustomClick = () => {
    if (customWeights) {
      setSelectedPerspective('custom')
      localStorage.setItem('compare-perspective', 'custom')
    } else {
      onCustomClick?.()
    }
  }

  return (
    <>
      {/* セクションヘッダー行 */}
      <tr className={styles.sectionHeader}>
        <td colSpan={colCount}>
          <div className={styles.scoreHeader}>
            <span className={styles.sectionTitle}>評価スコア</span>
            {perspectives.length > 0 && (
              <PerspectiveTabs
                perspectives={perspectives}
                selected={selectedPerspective}
                onSelect={handleSelect}
                onCustomClick={handleCustomClick}
                onHelpClick={onHelpClick}
              />
            )}
          </div>
        </td>
      </tr>

      {/* 総合スコア行 */}
      <tr>
        <td>総合スコア</td>
        {etfs.map((etf) => (
          <td key={etf.code} className={styles.scoreCell}>
            {isLoading ? (
              '...'
            ) : scores[etf.code]?.score != null ? (
              <span className={styles.totalScore}>
                {Math.round(scores[etf.code].score!)}点
              </span>
            ) : (
              '-'
            )}
          </td>
        ))}
      </tr>

      {/* 5軸スコア行 */}
      {AXIS_DEFINITIONS.map((axis) => (
        <tr key={axis.key} className={styles.axisRow}>
          <td>{axis.label}</td>
          {etfs.map((etf) => (
            <td key={etf.code} className={styles.scoreCell}>
              {isLoading
                ? '...'
                : scores[etf.code]?.axis_scores?.[axis.key] != null
                  ? Math.round(scores[etf.code].axis_scores![axis.key]!)
                  : '-'}
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}
