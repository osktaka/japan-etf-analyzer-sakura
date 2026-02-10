/** Market analysis page */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTagMomentum } from '../api'
import type { TagMomentumResponse } from '../api'
import { TagMomentumHeatmap } from '../components/market'
import { ROUTES, TAG_GROUP_ORDER, TAG_GROUP_LABELS } from '../utils/constants'
import {
  ALL_MOMENTUM_LABELS,
  MOMENTUM_STYLES,
  MomentumLabel,
} from '../utils/momentum'
import styles from './MarketPage.module.css'

export function MarketPage() {
  const navigate = useNavigate()
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [data, setData] = useState<TagMomentumResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async (category: string | null) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getTagMomentum(category || undefined)
      setData(result)
    } catch {
      setError('データの取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(selectedCategory)
  }, [selectedCategory, fetchData])

  const handleCategoryChange = (category: string | null) => {
    setSelectedCategory(category)
  }

  const handleTagClick = (tagId: number) => {
    navigate(`${ROUTES.HOME}?tags=${tagId}`)
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>市場分析</h2>

      <div className={styles.tabBar}>
        <button
          className={`${styles.tab} ${selectedCategory === null ? styles.tabActive : ''}`}
          onClick={() => handleCategoryChange(null)}
        >
          全体
        </button>
        {TAG_GROUP_ORDER.map((key) => (
          <button
            key={key}
            className={`${styles.tab} ${selectedCategory === key ? styles.tabActive : ''}`}
            onClick={() => handleCategoryChange(key)}
          >
            {TAG_GROUP_LABELS[key]}
          </button>
        ))}
      </div>

      {loading && <div className={styles.loading}>読み込み中...</div>}
      {error && <div className={styles.error}>{error}</div>}
      {!loading && !error && data && (
        <>
          <TagMomentumHeatmap data={data.tags} onTagClick={handleTagClick} />
          <div className={styles.legend}>
            {ALL_MOMENTUM_LABELS.map((label: MomentumLabel) => (
              <div key={label} className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{ backgroundColor: MOMENTUM_STYLES[label].color }}
                />
                <span className={styles.legendLabel}>{label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default MarketPage
