/** Compare page component */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ETFDetail,
  getETFDetail,
  ChartPeriod,
  PerformanceComparison,
  getPerformanceComparison,
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
import { TagBadge } from '../components/etf'
import { PriceChart } from '../components/chart'
import styles from './ComparePage.module.css'

export function ComparePage() {
  const { codes, removeCode, clearAll } = useCompareList()
  const [etfs, setEtfs] = useState<ETFDetail[]>([])
  const [performance, setPerformance] = useState<PerformanceComparison | null>(
    null
  )
  const [isLoading, setIsLoading] = useState(true)
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('1m')

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true)
      const [etfResults, perfData] = await Promise.all([
        Promise.all(codes.map((code) => getETFDetail(code))),
        getPerformanceComparison(codes),
      ])
      setEtfs(etfResults.filter((e): e is ETFDetail => e !== null))
      setPerformance(perfData)
      setIsLoading(false)
    }
    fetchData()
  }, [codes])

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
        <h1 className={styles.title}>ETF比較</h1>
        <button className="btn btn-secondary" onClick={clearAll}>
          リストをクリア
        </button>
      </div>

      {isLoading && <Loading />}

      {!isLoading && etfs.length > 0 && (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>項目</th>
                  {etfs.map((etf) => (
                    <th key={etf.code}>
                      <div className={styles.etfHeader}>
                        <span className={styles.code}>{etf.code}</span>
                        <span className={styles.name}>{etf.name}</span>
                        <button
                          className={styles.removeBtn}
                          onClick={() => removeCode(etf.code)}
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

          <div className={styles.chartSection}>
            <div className={styles.chartHeader}>
              <h2>価格チャート比較</h2>
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
          </div>
        </>
      )}
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
      {data && <PriceChart data={data.data} height={200} />}
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
