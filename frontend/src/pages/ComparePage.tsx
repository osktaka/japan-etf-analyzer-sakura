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
} from '../api'
import { useCompareList, useChartData } from '../hooks'
import {
  formatPrice,
  formatPercent,
  formatAssets,
  ROUTES,
  CHART_PERIODS,
} from '../utils'
import { Loading, ErrorMessage } from '../components/common'
import { FavoriteSelectModal, ETFDetailModal } from '../components/modal'
import { TagBadge } from '../components/etf'
import { PriceChart, OverlayChart } from '../components/chart'
import styles from './ComparePage.module.css'

type ChartMode = 'overlay' | 'individual'

export function ComparePage() {
  const { codes, removeCode, addCode, clearAll } = useCompareList()
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
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const initialCodesRef = useRef<string[]>(codes)

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
      setIsFavoriteModalOpen(false)

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

  if (codes.length === 0) {
    return (
      <div className={styles.empty}>
        <h1>比較リストが空です</h1>
        <p>トップページで銘柄を追加してください</p>
        <Link to={ROUTES.HOME} className="btn btn-primary">
          トップページへ
        </Link>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>銘柄比較</h1>
        <div className={styles.headerButtons}>
          <button
            className="btn btn-primary"
            onClick={() => setIsFavoriteModalOpen(true)}
          >
            お気に入りから追加
          </button>
          <button className="btn btn-secondary" onClick={handleClearAll}>
            リストをクリア
          </button>
        </div>
      </div>

      <FavoriteSelectModal
        isOpen={isFavoriteModalOpen}
        onClose={() => setIsFavoriteModalOpen(false)}
        onSelect={handleAddFromFavorite}
        existingCodes={codes}
      />

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
                    <th key={etf.code}>
                      <div className={styles.etfHeader}>
                        <span
                          className={styles.code}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setSelectedCode(etf.code)}
                        >
                          {etf.code}
                        </span>
                        <span
                          className={styles.name}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setSelectedCode(etf.code)}
                        >
                          {etf.name}
                        </span>
                        <button
                          className={styles.removeBtn}
                          onClick={() => handleRemove(etf.code)}
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
                  <td>市場価格</td>
                  {etfs.map((etf) => (
                    <td key={etf.code}>{formatPrice(etf.market_price)}</td>
                  ))}
                </tr>
                <tr>
                  <td>配当利回り</td>
                  {etfs.map((etf) => (
                    <td key={etf.code}>{formatPercent(etf.dividend_yield)}</td>
                  ))}
                </tr>
                <tr>
                  <td>信託報酬</td>
                  {etfs.map((etf) => (
                    <td key={etf.code}>{formatPercent(etf.expense_ratio)}</td>
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
