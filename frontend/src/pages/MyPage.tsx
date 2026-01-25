/** My page component */
import { useState } from 'react'
import { ETFCard } from '../components/etf/ETFCard'
import { ETFDetailModal } from '../components/modal/ETFDetailModal'
import { TradeForm, TradeList } from '../components/trade'
import { useAuth } from '../hooks/useAuth'
import { useFavorites } from '../hooks/useFavorites'
import { useTrades } from '../hooks/useTrades'
import { ETFSummary, CreateTradeRequest } from '../api/types'
import styles from './MyPage.module.css'

export function MyPage() {
  const { user } = useAuth()
  const { favorites, isLoading, error, toggleFavorite, isFavorite } =
    useFavorites()
  const {
    trades,
    isLoading: tradesLoading,
    error: tradesError,
    createTrade,
    updateTrade,
    deleteTrade,
  } = useTrades()
  const [selectedETF, setSelectedETF] = useState<ETFSummary | null>(null)
  const [showTradeForm, setShowTradeForm] = useState(false)

  const handleCardClick = (etf: ETFSummary) => {
    setSelectedETF(etf)
  }

  const handleCloseModal = () => {
    setSelectedETF(null)
  }

  const handleCreateTrade = async (data: CreateTradeRequest) => {
    const success = await createTrade(data)
    if (success) {
      setShowTradeForm(false)
    }
    return success
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>マイページ</h1>
        <p className={styles.welcome}>
          ようこそ、<strong>{user?.username}</strong> さん
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>お気に入り一覧</h2>

        {isLoading ? (
          <div className={styles.loading}>読み込み中...</div>
        ) : error ? (
          <div className={styles.error}>{error}</div>
        ) : favorites.length === 0 ? (
          <div className={styles.empty}>
            <p>お気に入りに登録されたETFはありません。</p>
            <p className={styles.hint}>
              検索結果やおすすめ一覧からお気に入りに追加できます。
            </p>
          </div>
        ) : (
          <div className={styles.grid}>
            {favorites.map((favorite) => (
              <ETFCard
                key={favorite.id}
                etf={favorite.etf}
                onClick={() => handleCardClick(favorite.etf)}
                isFavorite={isFavorite(favorite.etf_code)}
                onFavoriteToggle={() => toggleFavorite(favorite.etf_code)}
              />
            ))}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>売買履歴</h2>
          {!showTradeForm && (
            <button
              className={styles.addBtn}
              onClick={() => setShowTradeForm(true)}
            >
              取引を追加
            </button>
          )}
        </div>

        {showTradeForm && (
          <div className={styles.formWrapper}>
            <TradeForm
              onSubmit={handleCreateTrade}
              onCancel={() => setShowTradeForm(false)}
            />
          </div>
        )}

        <TradeList
          trades={trades}
          isLoading={tradesLoading}
          error={tradesError}
          onUpdate={updateTrade}
          onDelete={deleteTrade}
        />
      </section>

      {selectedETF && (
        <ETFDetailModal code={selectedETF.code} onClose={handleCloseModal} />
      )}
    </div>
  )
}

export default MyPage
