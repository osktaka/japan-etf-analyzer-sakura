/** Compare page component */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  ETFDetail,
  getETFDetail,
  ChartPeriod,
  ChartData,
  PerformanceComparison,
  getPerformanceComparison,
  getETFChart,
  getETFsChartBatch,
  userSettingsApi,
  CustomWeights,
} from '../api'
import {
  useCompareList,
  useChartData,
  useFavorites,
  useAuth,
  usePortfolio,
} from '../hooks'
import {
  formatPrice,
  formatPercent,
  formatAssets,
  ROUTES,
  CHART_PERIODS,
} from '../utils'
import { Loading, ErrorMessage, MomentumBadge } from '../components/common'
import {
  ETFListModal,
  ETFDetailModal,
  LoginPromptModal,
  WeightsHelpModal,
  CustomWeightsPromptModal,
  CustomWeightsModal,
} from '../components/modal'
import { CompareScoreSection, ETFSearchInput } from '../components/compare'
import { TagBadge } from '../components/etf'
import { FavoriteButton } from '../components/favorite'
import { PriceChart, OverlayChart } from '../components/chart'
import styles from './ComparePage.module.css'

type ChartMode = 'overlay' | 'individual'

export function ComparePage() {
  const { codes, removeCode, addCode, clearAll, canAdd, maxItems } =
    useCompareList()
  const { isFavorite, toggleFavorite } = useFavorites()
  const { isAuthenticated } = useAuth()
  const { holdings } = usePortfolio({ skipSummary: true })
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const [showWeightsHelp, setShowWeightsHelp] = useState(false)
  const [showCustomWeightsPrompt, setShowCustomWeightsPrompt] = useState(false)
  const [showCustomWeightsModal, setShowCustomWeightsModal] = useState(false)
  const [customWeights, setCustomWeights] = useState<CustomWeights | null>(null)
  const [loginPromptConfig, setLoginPromptConfig] = useState<{
    title?: string
    description?: string
  }>({})
  const [etfs, setEtfs] = useState<ETFDetail[]>([])
  const [performance, setPerformance] = useState<PerformanceComparison | null>(
    null
  )
  const [isLoading, setIsLoading] = useState(true)
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('1y')
  const [chartMode, setChartMode] = useState<ChartMode>('overlay')
  const [chartDatasets, setChartDatasets] = useState<
    Array<{ code: string; name: string; data: ChartData }>
  >([])
  const [isChartLoading, setIsChartLoading] = useState(false)
  const [isFavoriteModalOpen, setIsFavoriteModalOpen] = useState(false)
  const [isListModalOpen, setIsListModalOpen] = useState(false)
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const initialCodesRef = useRef<string[]>(codes)

  // カスタム重みの取得
  useEffect(() => {
    if (!isAuthenticated) return
    userSettingsApi.getSettings().then((settings) => {
      if (settings?.custom_weights) {
        setCustomWeights(settings.custom_weights)
      }
    })
  }, [isAuthenticated])

  const handleCustomClick = () => {
    if (!isAuthenticated) {
      setLoginPromptConfig({
        title: 'カスタム機能',
        description: 'カスタム重みづけ機能はログイン後にご利用いただけます。',
      })
      setShowLoginPrompt(true)
      return
    }
    if (!customWeights) {
      setShowCustomWeightsPrompt(true)
    }
  }

  const handleSaveCustomWeights = async (weights: CustomWeights) => {
    const response = await userSettingsApi.saveCustomWeights(weights)
    setCustomWeights(response.custom_weights)
  }

  // 初回読み込み時のみAPI取得
  useEffect(() => {
    const fetchData = async () => {
      const currentCodes = initialCodesRef.current
      if (currentCodes.length === 0) {
        setEtfs([])
        setPerformance(null)
        setIsLoading(false)
        return
      }
      setIsLoading(true)
      const [etfResults, perfData] = await Promise.all([
        Promise.all(currentCodes.map((code) => getETFDetail(code))),
        getPerformanceComparison(currentCodes),
      ])
      setEtfs(etfResults.filter((e): e is ETFDetail => e !== null))
      setPerformance(perfData)
      setIsLoading(false)
    }
    fetchData()
  }, [])

  // 銘柄削除時のローカル非表示（API再取得なし）
  const handleRemove = useCallback(
    (code: string) => {
      removeCode(code)
      setEtfs((prev) => prev.filter((etf) => etf.code !== code))
      setChartDatasets((prev) => prev.filter((ds) => ds.code !== code))
    },
    [removeCode]
  )

  // 銘柄追加時は新規銘柄のみAPI取得
  const handleAddFromFavorite = useCallback(
    async (code: string) => {
      addCode(code)

      // 新規銘柄のみAPI取得
      const newEtf = await getETFDetail(code)
      if (newEtf) {
        setEtfs((prev) => [...prev, newEtf])
        // チャートデータも取得
        const chartData = await getETFChart(code, chartPeriod)
        if (chartData) {
          setChartDatasets((prev) => [
            ...prev,
            { code, name: newEtf.name, data: chartData },
          ])
        }
      }
    },
    [addCode, chartPeriod]
  )

  // リストクリア（全Hooks呼び出し後に定義）
  const handleClearAll = useCallback(() => {
    clearAll()
    setEtfs([])
    setChartDatasets([])
    setPerformance(null)
  }, [clearAll])

  // お気に入りトグル
  const handleFavoriteToggle = useCallback(
    (code: string) => {
      if (!isAuthenticated) {
        setShowLoginPrompt(true)
        return
      }
      toggleFavorite(code)
    },
    [isAuthenticated, toggleFavorite]
  )

  // 保有銘柄のコードセット
  const holdingCodes = useMemo(
    () => new Set(holdings.map((h) => h.etf_code)),
    [holdings]
  )

  // チャートデータ再取得用の依存キー
  const etfCodesKey = useMemo(() => etfs.map((e) => e.code).join(','), [etfs])

  // Fetch chart data for overlay mode (period変更時のみ再取得)
  // Uses batch API to fetch all ETFs in a single request
  useEffect(() => {
    const fetchChartData = async () => {
      if (etfs.length === 0) {
        setChartDatasets([])
        return
      }
      setIsChartLoading(true)
      const codes = etfs.map((etf) => etf.code)
      const batchResult = await getETFsChartBatch(codes, chartPeriod)
      const datasets = etfs
        .map((etf) => {
          const chartData = batchResult[etf.code]
          return chartData
            ? { code: etf.code, name: etf.name, data: chartData }
            : null
        })
        .filter(
          (r): r is { code: string; name: string; data: ChartData } =>
            r !== null
        )
      setChartDatasets(datasets)
      setIsChartLoading(false)
    }
    fetchChartData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartPeriod, etfCodesKey])

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>銘柄比較</h1>
        <div className={styles.headerButtons}>
          <ETFSearchInput
            onSelect={handleAddFromFavorite}
            existingCodes={codes}
            canAdd={canAdd}
            maxItems={maxItems}
          />
          <button
            className="btn btn-primary"
            onClick={() => setIsListModalOpen(true)}
          >
            銘柄リスト
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setIsFavoriteModalOpen(true)}
          >
            お気に入り
          </button>
          <button className="btn btn-secondary" onClick={handleClearAll}>
            <span className={styles.desktopText}>リストをクリア</span>
            <span className={styles.mobileText}>クリア</span>
          </button>
        </div>
      </div>

      <ETFListModal
        isOpen={isListModalOpen}
        onClose={() => setIsListModalOpen(false)}
        mode="compare"
        etfs={etfs}
        onSelect={handleAddFromFavorite}
        onRemove={handleRemove}
        existingCodes={codes}
      />

      <ETFListModal
        isOpen={isFavoriteModalOpen}
        onClose={() => setIsFavoriteModalOpen(false)}
        mode="favorite"
        onSelect={handleAddFromFavorite}
        onRemove={handleRemove}
        existingCodes={codes}
      />

      {codes.length === 0 ? (
        <div className={styles.empty}>
          <p>比較リストが空です</p>
          <p>トップページで銘柄を追加してください</p>
          <Link to={ROUTES.HOME} className="btn btn-primary">
            トップページへ
          </Link>
        </div>
      ) : (
        <>
          {isLoading && <Loading />}

          {!isLoading && etfs.length > 0 && (
            <>
              <div className={styles.chartSection}>
                <div className={styles.chartHeader}>
                  <h2>価格チャート比較</h2>
                  <div className={styles.chartControls}>
                    <div className={styles.modeToggle}>
                      <button
                        className={`${styles.modeBtn} ${chartMode === 'overlay' ? styles.active : ''}`}
                        onClick={() => setChartMode('overlay')}
                      >
                        相対比較
                      </button>
                      <button
                        className={`${styles.modeBtn} ${chartMode === 'individual' ? styles.active : ''}`}
                        onClick={() => setChartMode('individual')}
                      >
                        個別
                      </button>
                    </div>
                    <div className={styles.periods}>
                      {CHART_PERIODS.map((p) => (
                        <button
                          key={p.id}
                          className={`${styles.periodBtn} ${chartPeriod === p.id ? styles.active : ''}`}
                          onClick={() => setChartPeriod(p.id as ChartPeriod)}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {isChartLoading && <Loading />}
                {!isChartLoading && chartMode === 'overlay' && (
                  <OverlayChart datasets={chartDatasets} height={400} />
                )}
                {!isChartLoading && chartMode === 'individual' && (
                  <div className={styles.charts}>
                    {etfs.map((etf) => (
                      <CompareChart
                        key={etf.code}
                        code={etf.code}
                        name={etf.name}
                        period={chartPeriod}
                      />
                    ))}
                  </div>
                )}
              </div>

              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>項目</th>
                      {etfs.map((etf) => (
                        <th
                          key={etf.code}
                          className={styles.clickableCell}
                          onClick={() => setSelectedCode(etf.code)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              setSelectedCode(etf.code)
                            }
                          }}
                          tabIndex={0}
                        >
                          <div className={styles.etfHeader}>
                            <span className={styles.codeRow}>
                              <FavoriteButton
                                isFavorite={isFavorite(etf.code)}
                                onClick={() => handleFavoriteToggle(etf.code)}
                                size="sm"
                                isHolding={holdingCodes.has(etf.code)}
                              />
                              <span className={styles.code}>{etf.code}</span>
                            </span>
                            <span className={styles.name}>{etf.name}</span>
                            <button
                              className={styles.removeBtn}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleRemove(etf.code)
                              }}
                            >
                              &times;
                            </button>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>カテゴリ</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>{etf.category?.name || '-'}</td>
                      ))}
                    </tr>
                    <tr>
                      <td>勢い</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>
                          <MomentumBadge label={etf.momentum_label} code={etf.code} />
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td>市場価格</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>{formatPrice(etf.market_price)}</td>
                      ))}
                    </tr>
                    <tr>
                      <td>配当利回り</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>
                          {formatPercent(etf.dividend_yield)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td>信託報酬</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>
                          {formatPercent(etf.expense_ratio)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td>純資産総額</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>{formatAssets(etf.total_assets)}</td>
                      ))}
                    </tr>
                    <tr>
                      <td>タグ</td>
                      {etfs.map((etf) => (
                        <td key={etf.code}>
                          <div className={styles.tags}>
                            {etf.tags.map((tag) => (
                              <TagBadge key={tag.id} tag={tag} size="sm" />
                            ))}
                          </div>
                        </td>
                      ))}
                    </tr>
                    {etfs.length > 0 && (
                      <CompareScoreSection
                        etfs={etfs}
                        colCount={etfs.length + 1}
                        onHelpClick={() => setShowWeightsHelp(true)}
                        onCustomClick={handleCustomClick}
                        customWeights={customWeights}
                      />
                    )}
                    {performance && (
                      <>
                        <tr className={styles.sectionHeader}>
                          <td colSpan={etfs.length + 1}>パフォーマンス</td>
                        </tr>
                        <tr>
                          <td>1ヶ月リターン</td>
                          {etfs.map((etf) => {
                            const perf = performance.items.find(
                              (p) => p.code === etf.code
                            )
                            return (
                              <td key={etf.code}>
                                <ReturnValue value={perf?.returns['1m']} />
                              </td>
                            )
                          })}
                        </tr>
                        <tr>
                          <td>3ヶ月リターン</td>
                          {etfs.map((etf) => {
                            const perf = performance.items.find(
                              (p) => p.code === etf.code
                            )
                            return (
                              <td key={etf.code}>
                                <ReturnValue value={perf?.returns['3m']} />
                              </td>
                            )
                          })}
                        </tr>
                        <tr>
                          <td>6ヶ月リターン</td>
                          {etfs.map((etf) => {
                            const perf = performance.items.find(
                              (p) => p.code === etf.code
                            )
                            return (
                              <td key={etf.code}>
                                <ReturnValue value={perf?.returns['6m']} />
                              </td>
                            )
                          })}
                        </tr>
                        <tr>
                          <td>1年リターン</td>
                          {etfs.map((etf) => {
                            const perf = performance.items.find(
                              (p) => p.code === etf.code
                            )
                            return (
                              <td key={etf.code}>
                                <ReturnValue value={perf?.returns['1y']} />
                              </td>
                            )
                          })}
                        </tr>
                        <tr>
                          <td>ボラティリティ</td>
                          {etfs.map((etf) => {
                            const perf = performance.items.find(
                              (p) => p.code === etf.code
                            )
                            return (
                              <td key={etf.code}>
                                {perf?.volatility != null
                                  ? `${perf.volatility.toFixed(2)}%`
                                  : '-'}
                              </td>
                            )
                          })}
                        </tr>
                      </>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      <ETFDetailModal
        code={selectedCode}
        onClose={() => setSelectedCode(null)}
        isInCompare={true}
        onCompareToggle={() => {
          if (selectedCode) {
            handleRemove(selectedCode)
            setSelectedCode(null)
          }
        }}
        isFavorite={selectedCode ? isFavorite(selectedCode) : false}
        onFavoriteToggle={() =>
          selectedCode && handleFavoriteToggle(selectedCode)
        }
        onCustomClick={handleCustomClick}
        customWeights={customWeights}
      />

      <LoginPromptModal
        isOpen={showLoginPrompt}
        onClose={() => setShowLoginPrompt(false)}
        title={loginPromptConfig.title}
        description={loginPromptConfig.description}
      />

      <WeightsHelpModal
        isOpen={showWeightsHelp}
        onClose={() => setShowWeightsHelp(false)}
        isAuthenticated={isAuthenticated ?? false}
        customWeights={customWeights}
        onEditCustom={() => setShowCustomWeightsModal(true)}
      />

      <CustomWeightsPromptModal
        isOpen={showCustomWeightsPrompt}
        onClose={() => setShowCustomWeightsPrompt(false)}
        onRegister={() => {
          setShowCustomWeightsPrompt(false)
          setShowCustomWeightsModal(true)
        }}
      />

      <CustomWeightsModal
        isOpen={showCustomWeightsModal}
        onClose={() => setShowCustomWeightsModal(false)}
        currentWeights={customWeights}
        onSave={handleSaveCustomWeights}
      />
    </div>
  )
}

function CompareChart({
  code,
  name,
  period,
}: {
  code: string
  name: string
  period: ChartPeriod
}) {
  const { data, isLoading, error } = useChartData(code, period)

  return (
    <div className={styles.chartCard}>
      <h3 className={styles.chartTitle}>
        {code} {name}
      </h3>
      {isLoading && <Loading />}
      {error && <ErrorMessage message="チャートの取得に失敗しました" />}
      {data && <PriceChart data={data.data} height={200} period={period} />}
    </div>
  )
}

function ReturnValue({ value }: { value: number | null | undefined }) {
  if (value == null) {
    return <span>-</span>
  }

  const isPositive = value >= 0
  const sign = isPositive ? '+' : ''
  const className = isPositive ? styles.positive : styles.negative

  return (
    <span className={className}>
      {sign}
      {value.toFixed(2)}%
    </span>
  )
}
