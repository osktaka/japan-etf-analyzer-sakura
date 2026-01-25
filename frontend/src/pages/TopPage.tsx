/** Top page component */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useETFSearch, useCompareList, useFavorites, useAuth } from '../hooks'
import { SearchBar, SearchResults } from '../components/search'
import { RecommendSection } from '../components/recommend'
import { ETFDetailModal, LoginPromptModal } from '../components/modal'
import { ROUTES, MAX_COMPARE_ITEMS } from '../utils'
import styles from './TopPage.module.css'

export function TopPage() {
  const navigate = useNavigate()
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const { items, isLoading, error, search, reset } = useETFSearch()
  const { count, isInList, toggleCode, canAdd } = useCompareList()
  const { isAuthenticated } = useAuth()
  const { isFavorite, toggleFavorite } = useFavorites()

  const handleSearch = (keyword: string) => {
    if (keyword.trim()) {
      search({ keyword })
    } else {
      reset()
    }
  }

  const handleCompareToggle = (code: string) => {
    if (!isInList(code) && !canAdd) {
      alert(`比較は最大${MAX_COMPARE_ITEMS}件までです`)
      return
    }
    toggleCode(code)
  }

  const handleFavoriteToggle = (code: string) => {
    if (!isAuthenticated) {
      setShowLoginPrompt(true)
      return
    }
    toggleFavorite(code)
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>日本ETF分析</h1>
        <p className={styles.subtitle}>
          ETFを検索・比較して、あなたに最適な投資先を見つけましょう
        </p>
        <div className={styles.searchWrapper}>
          <SearchBar
            onSearch={handleSearch}
            placeholder="銘柄コードまたは名前で検索..."
          />
        </div>
      </section>

      {items.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>検索結果</h2>
          <SearchResults
            items={items}
            isLoading={isLoading}
            error={error}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
          />
        </section>
      )}

      <RecommendSection
        onETFClick={setSelectedCode}
        isInCompare={isInList}
        onCompareToggle={handleCompareToggle}
        isFavorite={isFavorite}
        onFavoriteToggle={handleFavoriteToggle}
      />

      {count > 0 && (
        <div className={styles.compareBar}>
          <span>{count}件の銘柄を比較リストに追加中</span>
          <button
            className="btn btn-primary"
            onClick={() => navigate(ROUTES.COMPARE)}
          >
            比較する
          </button>
        </div>
      )}

      <ETFDetailModal
        code={selectedCode}
        onClose={() => setSelectedCode(null)}
        isInCompare={selectedCode ? isInList(selectedCode) : false}
        onCompareToggle={() =>
          selectedCode && handleCompareToggle(selectedCode)
        }
        isFavorite={selectedCode ? isFavorite(selectedCode) : false}
        onFavoriteToggle={() =>
          selectedCode && handleFavoriteToggle(selectedCode)
        }
      />

      <LoginPromptModal
        isOpen={showLoginPrompt}
        onClose={() => setShowLoginPrompt(false)}
      />
    </div>
  )
}
