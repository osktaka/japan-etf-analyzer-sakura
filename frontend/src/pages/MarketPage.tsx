/** Market analysis page */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { getTagMomentum } from '../api'
import type { TagMomentumResponse, TagMomentum } from '../api'
import { TagMomentumHeatmap } from '../components/market'
import { TagETFListModal } from '../components/modal'
import { TAG_GROUP_ORDER, TAG_GROUP_LABELS } from '../utils/constants'
import {
  ALL_MOMENTUM_LABELS,
  MOMENTUM_STYLES,
  MomentumLabel,
} from '../utils/momentum'
import styles from './MarketPage.module.css'

/** Per-category chart height (smaller than full-page view) */
const SECTION_HEIGHT = { pc: 280, mobile: 200 }

export function MarketPage() {
  const [data, setData] = useState<TagMomentumResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null)
  const [selectedTagName, setSelectedTagName] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getTagMomentum()
      setData(result)
    } catch {
      setError('データの取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  /** Group tags by category */
  const groupedTags = useMemo(() => {
    if (!data) return new Map<string, TagMomentum[]>()
    const map = new Map<string, TagMomentum[]>()
    for (const tag of data.tags) {
      const list = map.get(tag.category) ?? []
      list.push(tag)
      map.set(tag.category, list)
    }
    return map
  }, [data])

  const handleTagClick = (tagId: number) => {
    const tag = data?.tags.find((t) => t.id === tagId)
    setSelectedTagId(tagId)
    setSelectedTagName(tag?.name ?? '')
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>市場分析</h2>

      {loading && <div className={styles.loading}>読み込み中...</div>}
      {error && <div className={styles.error}>{error}</div>}
      {!loading && !error && data && (
        <>
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>全体</h3>
            <TagMomentumHeatmap data={data.tags} onTagClick={handleTagClick} />
          </section>
          {TAG_GROUP_ORDER.map((key) => {
            const tags = groupedTags.get(key)
            if (!tags || tags.length === 0) return null
            return (
              <section key={key} className={styles.section}>
                <h3 className={styles.sectionTitle}>{TAG_GROUP_LABELS[key]}</h3>
                <TagMomentumHeatmap
                  data={tags}
                  onTagClick={handleTagClick}
                  height={SECTION_HEIGHT}
                />
              </section>
            )
          })}
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
      <TagETFListModal
        isOpen={selectedTagId !== null}
        onClose={() => setSelectedTagId(null)}
        tagId={selectedTagId ?? 0}
        tagName={selectedTagName}
      />
    </div>
  )
}

export default MarketPage
