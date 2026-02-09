/** My page component */
import { useState, useMemo, useEffect } from 'react'
import { ETFCard } from '../components/etf/ETFCard'
import {
  ETFDetailModal,
  TradeFormModal,
  TradeHistoryModal,
  CustomWeightsPromptModal,
  CustomWeightsModal,
  WeightsHelpModal,
} from '../components/modal'
import {
  PortfolioSummary,
  HoldingsList,
  PortfolioValueChart,
  HoldingsTreeMap,
} from '../components/portfolio'
import { PerspectiveTabs } from '../components/recommend'
import { useFavorites } from '../hooks/useFavorites'
import { useCompareList } from '../hooks/useCompareList'
import { usePortfolio } from '../hooks/usePortfolio'
import { useAuth } from '../hooks/useAuth'
import { ETFSummary, Perspective, CustomWeights } from '../api/types'
import { recommendApi } from '../api/recommend'
import { userSettingsApi } from '../api/userSettings'
import styles from './MyPage.module.css'

export function MyPage() {
  const [perspective, setPerspective] = useState<string>(() => {
    return localStorage.getItem('mypage-perspective') || 'balance'
  })
  const [perspectives, setPerspectives] = useState<Perspective[]>([])
  const [sortEnabled, setSortEnabled] = useState(() => {
    const stored = localStorage.getItem('mypage-sort-enabled')
    return stored === 'true'
  })
  const [showCustomWeightsPromptModal, setShowCustomWeightsPromptModal] =
    useState(false)
  const [showCustomWeightsModal, setShowCustomWeightsModal] = useState(false)
  const [showWeightsHelp, setShowWeightsHelp] = useState(false)
  const [customWeights, setCustomWeights] = useState<CustomWeights | null>(null)

  const { isAuthenticated } = useAuth()

  const { favorites, isLoading, error, toggleFavorite, isFavorite, refresh } =
    useFavorites(perspective, 'full')
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
  const [tradeHistoryCode, setTradeHistoryCode] = useState<string>('')

  // Save perspective to localStorage
  useEffect(() => {
    localStorage.setItem('mypage-perspective', perspective)
  }, [perspective])

  // Save sort enabled state to localStorage
  useEffect(() => {
    localStorage.setItem('mypage-sort-enabled', String(sortEnabled))
  }, [sortEnabled])

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

  // Fetch custom weights on mount
  useEffect(() => {
    const fetchCustomWeights = async () => {
      if (!isAuthenticated) return
      try {
        const settings = await userSettingsApi.getSettings()
        setCustomWeights(settings.custom_weights)
      } catch (err) {
        console.error('Failed to fetch custom weights:', err)
      }
    }
    fetchCustomWeights()
  }, [isAuthenticated])

  // Refresh favorites when perspective changes
  useEffect(() => {
    refresh(perspective, 'full')
  }, [perspective, refresh])

  // 保有中銘柄のコードSetを作成（お気に入りカードの保有中表示用）
  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )
  const isHolding = (code: string): boolean => holdingCodes.has(code)

  // Sort favorites by score if enabled
  const sortedFavorites = useMemo(() => {
    if (!sortEnabled) return favorites
    return [...favorites].sort((a, b) => {
      const scoreA = a.etf.score ?? 0
      const scoreB = b.etf.score ?? 0
      return scoreB - scoreA // 降順
    })
  }, [favorites, sortEnabled])

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

  const handleHistoryClick = (code: string) => {
    setTradeHistoryCode(code)
    setShowTradeHistoryModal(true)
  }

  const handleCloseTradeHistory = () => {
    setShowTradeHistoryModal(false)
    setTradeHistoryCode('')
  }

  const handleCustomClick = () => {
    if (!customWeights) {
      // 未設定時はプロンプトモーダルを表示
      setShowCustomWeightsPromptModal(true)
    } else {
      // 設定済み時はカスタム切り口に切り替え
      setPerspective('custom')
    }
  }

  const handleEditCustom = () => {
    setShowCustomWeightsModal(true)
  }

  const handleSaveCustomWeights = async (weights: CustomWeights) => {
    const response = await userSettingsApi.saveCustomWeights(weights)
    setCustomWeights(response.custom_weights)
    setPerspective('custom')
    refresh('custom', 'full')
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>マイページ</h1>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>ポートフォリオ</h2>

        {summary && <PortfolioSummary summary={summary} />}

        <div className={styles.chartSection}>
          <PortfolioValueChart />
          {holdings.length > 0 && (
            <HoldingsTreeMap
              holdings={holdings}
              onETFClick={handleHoldingClick}
            />
          )}
        </div>

        <HoldingsList
          holdings={holdings}
          isLoading={portfolioLoading}
          error={portfolioError}
          onETFClick={handleHoldingClick}
          onHistoryClick={handleHistoryClick}
          isInCompare={isInCompare}
          onCompareToggle={toggleCompare}
          onTradeHistory={() => setShowTradeHistoryModal(true)}
          onAddTrade={() => setShowTradeFormModal(true)}
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
              onCustomClick={handleCustomClick}
              onHelpClick={() => setShowWeightsHelp(true)}
            />
            <div className={styles.buttonGroup}>
              {isAuthenticated && (
                <button
                  className={styles.secondaryBtn}
                  onClick={handleEditCustom}
                  type="button"
                >
                  カスタムを編集
                </button>
              )}
              <button
                className={`${styles.sortToggle} ${sortEnabled ? styles.sortActive : ''}`}
                onClick={() => setSortEnabled(!sortEnabled)}
                type="button"
              >
                ソート{sortEnabled ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>
        )}

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
            {sortedFavorites.map((favorite) => (
              <ETFCard
                key={favorite.id}
                etf={favorite.etf}
                onClick={() => handleCardClick(favorite.etf)}
                isFavorite={isFavorite(favorite.etf_code)}
                onFavoriteToggle={() => toggleFavorite(favorite.etf_code)}
                showCompareButton
                isSelected={isInCompare(favorite.etf_code)}
                onCompareToggle={() => toggleCompare(favorite.etf_code)}
                isHolding={isHolding(favorite.etf_code)}
                perspective={perspective}
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
            onCustomClick={handleCustomClick}
            customWeights={customWeights}
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
        onClose={handleCloseTradeHistory}
        initialSearch={tradeHistoryCode}
      />

      <CustomWeightsPromptModal
        isOpen={showCustomWeightsPromptModal}
        onClose={() => setShowCustomWeightsPromptModal(false)}
        onRegister={() => {
          setShowCustomWeightsPromptModal(false)
          setShowCustomWeightsModal(true)
        }}
      />

      <CustomWeightsModal
        isOpen={showCustomWeightsModal}
        onClose={() => setShowCustomWeightsModal(false)}
        currentWeights={customWeights}
        onSave={handleSaveCustomWeights}
      />

      <WeightsHelpModal
        isOpen={showWeightsHelp}
        onClose={() => setShowWeightsHelp(false)}
        isAuthenticated={isAuthenticated}
        customWeights={customWeights}
        onEditCustom={handleEditCustom}
      />
    </div>
  )
}

export default MyPage
