/** Top page component */
import { useState, useMemo, useRef, useEffect } from 'react'
import type { SortField } from '../api'
import {
  useCompareList,
  useFavorites,
  useAuth,
  usePortfolio,
  useTopPagePerformanceData,
  useTopPageDisplayMode,
  useTopPageSearch,
  type SearchOverrides,
} from '../hooks'
import {
  SearchResults,
  FilterPanel,
  ETFTableView,
  SectionControls,
  ColumnVisibilitySelector,
} from '../components/search'
import { RecommendSection } from '../components/recommend'
import {
  ETFDetailModal,
  LoginPromptModal,
  CustomWeightsPromptModal,
  CustomWeightsModal,
  WeightsHelpModal,
} from '../components/modal'
import { Pagination } from '../components/common'
import { userSettingsApi, CustomWeights } from '../api'
import styles from './TopPage.module.css'

export function TopPage() {
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [loginPromptConfig, setLoginPromptConfig] = useState<{
    title: string
    description: string
  } | null>(null)
  const [showCustomWeightsPromptModal, setShowCustomWeightsPromptModal] =
    useState(false)
  const [showCustomWeightsModal, setShowCustomWeightsModal] = useState(false)
  const [showWeightsHelpModal, setShowWeightsHelpModal] = useState(false)
  const [customWeights, setCustomWeights] = useState<CustomWeights | null>(null)
  // おすすめタブの状態（URLとlocalStorageから復元）
  const [recommendTab, setRecommendTab] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    const tabFromUrl = params.get('tab')
    if (tabFromUrl) return tabFromUrl
    return localStorage.getItem('recommend-perspective') || 'balance'
  })

  const {
    isInList,
    toggleCode,
    canAdd,
    codes: compareCodes,
    count: compareCount,
    maxItems,
  } = useCompareList()
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth()
  const { isFavorite, toggleFavorite, favoriteCodes } = useFavorites()
  const { holdings } = usePortfolio()

  // 保有コードのSetを作成（quantity > 0の銘柄のみ）
  const holdingCodes = useMemo(
    () =>
      new Set(holdings.filter((h) => h.quantity > 0).map((h) => h.etf_code)),
    [holdings]
  )

  // isHolding関数 - ETFCard/ETFTableViewに渡すために使用
  const isHolding = (code: string): boolean => holdingCodes.has(code)

  // コールバック用のref（循環依存を解決）
  const currentSortRef = useRef<SortField>('score_balance') // 初期perspective=balanceに対応
  const sortUpdateRef = useRef<(sort: never, order: never) => void>(() => {})
  const searchRequestRef = useRef<(overrides?: SearchOverrides) => void>(
    () => {}
  )

  // 表示モード関連のフック
  const displayModeHook = useTopPageDisplayMode({
    getCurrentSort: () => currentSortRef.current,
    currentOrder: 'desc',
    onSortUpdate: (sort, order) =>
      sortUpdateRef.current(sort as never, order as never),
    onSearchRequest: (overrides) => searchRequestRef.current(overrides),
  })

  const {
    viewMode,
    displayMode,
    scoringMode,
    selectedPerspective,
    selectedPeriods,
    returnType,
    setDisplayMode,
    setSelectedPerspective,
    setSelectedPeriods,
    setReturnType,
    annualized,
    setAnnualized,
    commonColumnVisibility,
    scoreColumnVisibility,
    momentumVisible,
    setCommonColumnVisibility,
    setScoreColumnVisibility,
    setMomentumVisible,
    handleViewModeChange,
    handleScoringModeChange,
    getInitialViewMode,
  } = displayModeHook

  // 検索関連のフック
  const searchHook = useTopPageSearch({
    returnType,
    scoringMode,
    selectedPerspective,
    customWeights,
    favoriteCodes,
    holdingCodes,
    compareCodes,
    getInitialViewMode,
    viewMode,
    displayMode,
  })

  const {
    currentKeyword,
    currentFilters,
    currentSort,
    currentOrder,
    currentPage,
    hasSearched,
    favoritesOnly,
    holdingsOnly,
    compareOnly,
    totalPages,
    setCurrentSort,
    setCurrentOrder,
    setFavoritesOnly,
    setHoldingsOnly,
    setCompareOnly,
    items,
    total,
    isLoading,
    error,
    handleSearch,
    handleFilter,
    handleSortChange,
    handlePageChange,
    executeSearch,
    etfListRef,
    updateURL,
  } = searchHook

  // コールバックrefの更新
  useEffect(() => {
    sortUpdateRef.current = (sort: never, order: never) => {
      setCurrentSort(sort)
      setCurrentOrder(order)
    }
    searchRequestRef.current = (overrides) => executeSearch(overrides)
  }, [setCurrentSort, setCurrentOrder, executeSearch])

  // currentSortRefの更新
  useEffect(() => {
    currentSortRef.current = currentSort
  }, [currentSort])

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

  // 未ログイン時にcustomが選択されていたらbalanceにフォールバック
  useEffect(() => {
    // 認証状態の確認中は何もしない
    if (isAuthLoading) return
    if (!isAuthenticated && recommendTab === 'custom') {
      setRecommendTab('balance')
      localStorage.setItem('recommend-perspective', 'balance')
    }
  }, [isAuthLoading, isAuthenticated, recommendTab])

  // パフォーマンスデータとスコアデータの取得
  const { performance, scores } = useTopPagePerformanceData({
    viewMode,
    displayMode,
    scoringMode,
    items,
  })

  const handleRecommendTabChange = (tab: string) => {
    setRecommendTab(tab)
    localStorage.setItem('recommend-perspective', tab)
    updateURL({ tab })
  }

  const handleCompareToggle = (code: string) => {
    if (!isInList(code) && !canAdd) {
      const message = isAuthenticated
        ? `銘柄比較は最大${maxItems}件までです`
        : `銘柄比較は最大${maxItems}件までです（ログインすると10件まで比較できます）`
      alert(message)
      return
    }
    toggleCode(code)
  }

  const handleFavoriteToggle = (code: string) => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: 'お気に入り機能',
        description: 'お気に入り機能はログイン後にご利用いただけます。',
      })
      return
    }
    toggleFavorite(code)
  }

  // お気に入りフィルター変更ハンドラ（未ログイン時はログイン促進）
  const handleFavoritesOnlyChange = (value: boolean) => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: 'お気に入り機能',
        description: 'お気に入り機能はログイン後にご利用いただけます。',
      })
      return
    }
    setFavoritesOnly(value)
  }

  // 保有中フィルター変更ハンドラ（未ログイン時はログイン促進）
  const handleHoldingsOnlyChange = (value: boolean) => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: '保有銘柄機能',
        description: '保有銘柄機能はログイン後にご利用いただけます。',
      })
      return
    }
    setHoldingsOnly(value)
  }

  const handleCustomClick = () => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: 'カスタム機能',
        description: 'カスタム重みづけ機能はログイン後にご利用いただけます。',
      })
      return
    }
    if (!customWeights) {
      // 未設定時はプロンプトモーダルを表示
      setShowCustomWeightsPromptModal(true)
    } else {
      // 設定済み時はカスタム切り口に切り替え
      handleRecommendTabChange('custom')
    }
  }

  const handleSearchCustomClick = () => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: 'カスタム機能',
        description: 'カスタム重みづけ機能はログイン後にご利用いただけます。',
      })
      return
    }
    if (!customWeights) {
      setShowCustomWeightsPromptModal(true)
    } else {
      setSelectedPerspective('custom')
    }
  }

  const handleHelpClick = () => {
    setShowWeightsHelpModal(true)
  }

  const handleEditCustom = () => {
    setShowCustomWeightsModal(true)
  }

  const handleSaveCustomWeights = async (weights: CustomWeights) => {
    const response = await userSettingsApi.saveCustomWeights(weights)
    setCustomWeights(response.custom_weights)
    handleRecommendTabChange('custom')
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>東証ETF銘柄の比較分析</h1>
        <p className={styles.subtitle}>
          銘柄を検索・比較して、あなたに最適な投資先を見つけましょう
        </p>
      </section>

      {/* おすすめセクションを上部に移動 */}
      <RecommendSection
        onETFClick={setSelectedCode}
        isInCompare={isInList}
        onCompareToggle={handleCompareToggle}
        isFavorite={isFavorite}
        onFavoriteToggle={handleFavoriteToggle}
        isHolding={isHolding}
        selectedPerspective={recommendTab}
        onSelectPerspective={handleRecommendTabChange}
        isAuthenticated={isAuthenticated}
        customWeights={customWeights}
        onCustomClick={handleCustomClick}
        onEditCustom={handleEditCustom}
      />

      {/* 検索・一覧セクション */}
      <section ref={etfListRef} className={styles.section}>
        <div className={styles.searchHeader}>
          <h2 className={styles.searchTitle}>銘柄を探す</h2>
        </div>

        <div className={styles.filterSection}>
          <FilterPanel
            onFilter={handleFilter}
            onSearch={handleSearch}
            initialParams={currentFilters}
            initialKeyword={currentKeyword}
            holdingsOnly={holdingsOnly}
            onHoldingsOnlyChange={handleHoldingsOnlyChange}
            holdingsCount={holdingCodes.size}
            favoritesOnly={favoritesOnly}
            onFavoritesOnlyChange={handleFavoritesOnlyChange}
            favoritesCount={favoriteCodes.size}
            compareOnly={compareOnly}
            onCompareOnlyChange={setCompareOnly}
            compareCount={compareCount}
          />
        </div>

        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>
            {hasSearched ? '検索結果' : '全銘柄一覧'}
          </h2>
          <SectionControls
            viewMode={viewMode}
            displayMode={displayMode}
            scoringMode={scoringMode}
            selectedPerspective={selectedPerspective}
            returnType={returnType}
            annualized={annualized}
            onViewModeChange={handleViewModeChange}
            onDisplayModeChange={setDisplayMode}
            onScoringModeChange={handleScoringModeChange}
            onPerspectiveChange={setSelectedPerspective}
            onReturnTypeChange={setReturnType}
            onAnnualizedChange={setAnnualized}
            isAuthenticated={isAuthenticated}
            customWeights={customWeights}
            onCustomClick={handleSearchCustomClick}
            onHelpClick={handleHelpClick}
          />
        </div>
        <div className={styles.resultCount}>
          {viewMode === 'table' && (
            <ColumnVisibilitySelector
              displayMode={displayMode}
              commonColumnVisibility={commonColumnVisibility}
              onCommonColumnVisibilityChange={setCommonColumnVisibility}
              scoreColumnVisibility={scoreColumnVisibility}
              onScoreColumnVisibilityChange={setScoreColumnVisibility}
              selectedPeriods={selectedPeriods}
              onPeriodsChange={setSelectedPeriods}
              momentumVisible={momentumVisible}
              onMomentumVisibleChange={setMomentumVisible}
            />
          )}
          <span className={styles.resultCountText}>{total}件</span>
        </div>
        {viewMode === 'card' ? (
          <SearchResults
            items={items}
            isLoading={isLoading}
            error={error}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
            isHolding={isHolding}
            perspective={selectedPerspective}
          />
        ) : (
          <ETFTableView
            items={items}
            performance={performance}
            scores={scores}
            displayMode={displayMode}
            selectedPeriods={selectedPeriods}
            selectedPerspective={selectedPerspective}
            returnType={returnType}
            annualized={annualized}
            commonColumnVisibility={commonColumnVisibility}
            scoreColumnVisibility={scoreColumnVisibility}
            momentumVisible={momentumVisible}
            onETFClick={setSelectedCode}
            isInCompare={isInList}
            onCompareToggle={handleCompareToggle}
            isFavorite={isFavorite}
            onFavoriteToggle={handleFavoriteToggle}
            isHolding={isHolding}
            sortField={currentSort}
            sortOrder={currentOrder}
            onSortChange={handleSortChange}
          />
        )}
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </section>

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
        initialPerspective={selectedPerspective}
        onCustomClick={handleCustomClick}
        customWeights={customWeights}
      />

      <LoginPromptModal
        isOpen={loginPromptConfig !== null}
        onClose={() => setLoginPromptConfig(null)}
        title={loginPromptConfig?.title}
        description={loginPromptConfig?.description}
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
        isOpen={showWeightsHelpModal}
        onClose={() => setShowWeightsHelpModal(false)}
        isAuthenticated={isAuthenticated}
        customWeights={customWeights}
        onEditCustom={handleEditCustom}
      />
    </div>
  )
}
