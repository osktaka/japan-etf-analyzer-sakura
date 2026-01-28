/** My page component */
import { useState } from 'react'
import { ETFCard } from '../components/etf/ETFCard'
import {
  ETFDetailModal,
  TradeFormModal,
  TradeHistoryModal,
} from '../components/modal'
import { PortfolioSummary, HoldingsList } from '../components/portfolio'
import { useAuth } from '../hooks/useAuth'
import { useFavorites } from '../hooks/useFavorites'
import { useCompareList } from '../hooks/useCompareList'
import { usePortfolio } from '../hooks/usePortfolio'
import { ETFSummary } from '../api/types'
import styles from './MyPage.module.css'

export function MyPage() {
  const { user } = useAuth()
  const { favorites, isLoading, error, toggleFavorite, isFavorite } =
    useFavorites()
  const { isInList: isInCompare, toggleCode: toggleCompare } = useCompareList()
  const {
    holdings,
    summary,
    isLoading: portfolioLoading,
    error: portfolioError,
    refresh: refreshPortfolio,
  } = usePortfolio()
  const [selectedETF, setSelectedETF] = useState<ETFSummary | null>(null)
  const [selectedETFCode, setSelectedETFCode] = useState<string | null>(null)
  const [showTradeFormModal, setShowTradeFormModal] = useState(false)
  const [showTradeHistoryModal, setShowTradeHistoryModal] = useState(false)

  const handleCardClick = (etf: ETFSummary) => {
    setSelectedETF(etf)
  }

  const handleCloseModal = () => {
    setSelectedETF(null)
    setSelectedETFCode(null)
  }

  const handleHoldingClick = (code: string) => {
    setSelectedETFCode(code)
  }

  const handleTradeSuccess = () => {
    refreshPortfolio()
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
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>ポートフォリオ</h2>
          <div className={styles.buttonGroup}>
            <button
              className={styles.secondaryBtn}
              onClick={() => setShowTradeHistoryModal(true)}
            >
              取引履歴
            </button>
            <button
              className={styles.addBtn}
              onClick={() => setShowTradeFormModal(true)}
            >
              取引を追加
            </button>
          </div>
        </div>

        {summary && <PortfolioSummary summary={summary} />}

        <HoldingsList
          holdings={holdings}
          isLoading={portfolioLoading}
          error={portfolioError}
          onETFClick={handleHoldingClick}
        />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>お気に入り一覧</h2>

        {isLoading ? (
          <div className={styles.loading}>読み込み中...</div>
        ) : error ? (
          <div className={styles.error}>{error}</div>
        ) : favorites.length === 0 ? (
          <div className={styles.empty}>
            <p>お気に入りに登録された銘柄はありません。</p>
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
                showCompareButton
                isSelected={isInCompare(favorite.etf_code)}
                onCompareToggle={() => toggleCompare(favorite.etf_code)}
              />
            ))}
          </div>
        )}
      </section>

      {(() => {
        const modalCode = selectedETF?.code ?? selectedETFCode
        if (!modalCode) return null
        return (
          <ETFDetailModal
            code={modalCode}
            onClose={handleCloseModal}
            isFavorite={isFavorite(modalCode)}
            onFavoriteToggle={() => toggleFavorite(modalCode)}
            isInCompare={isInCompare(modalCode)}
            onCompareToggle={() => toggleCompare(modalCode)}
          />
        )
      })()}

      <TradeFormModal
        isOpen={showTradeFormModal}
        onClose={() => setShowTradeFormModal(false)}
        onSuccess={handleTradeSuccess}
      />

      <TradeHistoryModal
        isOpen={showTradeHistoryModal}
        onClose={() => setShowTradeHistoryModal(false)}
      />
    </div>
  )
}

export default MyPage
