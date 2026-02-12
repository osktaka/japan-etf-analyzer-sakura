/** Demo page component */
import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ETFCard } from '../components/etf/ETFCard'
import { ETFDetailModal } from '../components/modal'
import {
  PortfolioSummary,
  HoldingsList,
  PortfolioValueChart,
  HoldingsTreeMap,
} from '../components/portfolio'
import { PerspectiveTabs } from '../components/recommend'
import { useDemoPortfolio } from '../hooks/useDemoPortfolio'
import { useDemoFavorites } from '../hooks/useDemoFavorites'
import { ETFSummary, Perspective } from '../api/types'
import { recommendApi } from '../api/recommend'
import { ROUTES } from '../utils'
import styles from './DemoPage.module.css'

export function DemoPage() {
  const [perspective, setPerspective] = useState<string>('balance')
  const [perspectives, setPerspectives] = useState<Perspective[]>([])

  const { holdings, summary, isLoading: portfolioLoading, error: portfolioError } =
    useDemoPortfolio()
  const {
    favorites,
    isLoading: favoritesLoading,
    error: favoritesError,
  } = useDemoFavorites(perspective)

  const [selectedETF, setSelectedETF] = useState<ETFSummary | null>(null)
  const [selectedETFCode, setSelectedETFCode] = useState<string | null>(null)

  // Fetch perspectives on mount
  useEffect(() => {
    const fetchPerspectives = async () => {
      try {
        const data = await recommendApi.getPerspectives()
        setPerspectives(data)
      } catch (err) {
        console.error('Failed to fetch perspectives:', err)
      }
    }
    fetchPerspectives()
  }, [])

  // 保有中銘柄のコードSet
  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )
  const isHolding = (code: string): boolean => holdingCodes.has(code)

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

  return (
    <div className={styles.container}>
      <div className={styles.banner}>
        これはデモデータです。実際のポートフォリオを管理するには
        <Link to={ROUTES.LOGIN} className={styles.bannerLink}>ログイン</Link>
        してください。
      </div>

      <div className={styles.header}>
        <h1 className={styles.title}>マイページ（デモ）</h1>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>ポートフォリオ</h2>

        {summary && <PortfolioSummary summary={summary} />}

        <div className={styles.chartSection}>
          <PortfolioValueChart demoMode />
          {holdings.length > 0 && summary && (
            <HoldingsTreeMap
              holdings={holdings}
              cashBalance={summary.cash_balance}
              onETFClick={handleHoldingClick}
            />
          )}
        </div>

        <HoldingsList
          holdings={holdings}
          isLoading={portfolioLoading}
          error={portfolioError}
          onETFClick={handleHoldingClick}
          readOnly
        />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>お気に入り一覧</h2>

        {perspectives.length > 0 && (
          <div className={styles.favoritesControls}>
            <PerspectiveTabs
              perspectives={perspectives}
              selected={perspective}
              onSelect={setPerspective}
            />
          </div>
        )}

        {favoritesLoading ? (
          <div className={styles.loading}>読み込み中...</div>
        ) : favoritesError ? (
          <div className={styles.error}>{favoritesError}</div>
        ) : favorites.length === 0 ? (
          <div className={styles.empty}>
            <p>お気に入りに登録された銘柄はありません。</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {favorites.map((favorite) => (
              <ETFCard
                key={favorite.id}
                etf={favorite.etf}
                onClick={() => handleCardClick(favorite.etf)}
                isFavorite={true}
                isHolding={isHolding(favorite.etf_code)}
                perspective={perspective}
                readOnly
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
          />
        )
      })()}
    </div>
  )
}

export default DemoPage
