/** Guide Recommend Page - Explanation of 6 perspectives */
import { Link } from 'react-router-dom'
import { SEOHead } from '../../components/common'
import { ROUTES } from '../../utils'
import styles from './GuidePage.module.css'

export function GuideRecommendPage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="おすすめ銘柄 - Japan ETF Analyzer"
        description="Japan ETF Analyzerの6つの切り口（配当重視、低コスト、安定性、取引規模、成長性、バランス）について詳しく解説します。"
      />

      <h1 className={styles.pageTitle}>おすすめ銘柄</h1>

      <p className={styles.text}>
        トップページ上部の「おすすめ銘柄」セクションでは、6つの異なる切り口から
        ETF銘柄をランキング形式で表示しています。投資目的に合った切り口を選んでください。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>6つの切り口</h2>
        <div className={styles.perspectiveGrid}>
          <div className={styles.perspectiveCard} data-perspective="dividend">
            <h3 className={styles.perspectiveTitle}>配当収入</h3>
            <p className={styles.perspectiveText}>
              配当利回り（年間配当金を株価で割った比率）が高く、定期的な配当収入を期待できる銘柄。配当金による定期収入を重視する投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              配当力（50%）、安定性（20%）、コスト効率・取引規模・リターン実績
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="low-cost">
            <h3 className={styles.perspectiveTitle}>低コスト</h3>
            <p className={styles.perspectiveText}>
              信託報酬（ETFの運用管理にかかる年間コスト）が低く、長期保有でコストを抑えられる銘柄。保有コストを最小化したい長期投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              コスト効率（50%）、安定性（20%）、配当力・取引規模・リターン実績
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="stability">
            <h3 className={styles.perspectiveTitle}>安定性</h3>
            <p className={styles.perspectiveText}>
              純資産総額（ファンドに集まっている資金の総額）が大きく、安心して保有できる銘柄。リスクを抑えたい初心者・保守的な投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              安定性（40%）、コスト効率・取引規模（各20%）、配当力・リターン実績
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="volume">
            <h3 className={styles.perspectiveTitle}>取引規模</h3>
            <p className={styles.perspectiveText}>
              出来高（1日に取引された口数）が多く、売買が成立しやすい銘柄。流動性を重視する短期トレーダー・アクティブ投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              取引規模（50%）、安定性（20%）、配当力・コスト効率・リターン実績
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="growth">
            <h3 className={styles.perspectiveTitle}>成長性</h3>
            <p className={styles.perspectiveText}>
              過去の値上がり実績が良好な銘柄。値上がり益（キャピタルゲイン）を重視する成長志向の投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              リターン実績（50%）、安定性（20%）、配当力・コスト効率・取引規模
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="balance">
            <h3 className={styles.perspectiveTitle}>バランス</h3>
            <p className={styles.perspectiveText}>
              複数の観点でバランス良く評価された銘柄。特定の軸に偏らず、総合的に優れた銘柄を探している投資家におすすめです。
            </p>
            <div className={styles.perspectiveMetrics}>
              重視指標:
              配当力・コスト効率・安定性・取引規模・リターン実績（各20%均等）
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>5つの評価軸</h2>
        <p className={styles.text}>
          すべての銘柄は以下の5つの軸で評価され、切り口ごとの重み付けによって総合スコアが算出されます。
        </p>
        <div className={styles.axisGrid}>
          <div className={styles.axisCard}>
            <h3 className={styles.axisTitle}>配当力</h3>
            <p className={styles.axisText}>
              配当金による収益性を評価します。配当利回りが高いほどスコアが高くなります。
            </p>
            <div className={styles.axisMetric}>使用指標: 配当利回り</div>
          </div>

          <div className={styles.axisCard}>
            <h3 className={styles.axisTitle}>コスト効率</h3>
            <p className={styles.axisText}>
              保有コストの低さを評価します。信託報酬が低いほどスコアが高くなります。
            </p>
            <div className={styles.axisMetric}>使用指標: 信託報酬率</div>
          </div>

          <div className={styles.axisCard}>
            <h3 className={styles.axisTitle}>安定性</h3>
            <p className={styles.axisText}>
              純資産規模による安定性・信頼性を評価します。純資産が大きいほどスコアが高くなります。
            </p>
            <div className={styles.axisMetric}>使用指標: 純資産総額</div>
          </div>

          <div className={styles.axisCard}>
            <h3 className={styles.axisTitle}>取引規模</h3>
            <p className={styles.axisText}>
              売買のしやすさを評価します。売買代金・出来高が大きく、乖離率が小さいほどスコアが高くなります。
            </p>
            <div className={styles.axisMetric}>
              使用指標: 売買代金（50%）、平均出来高（30%）、乖離率（ETFの市場価格と基準価額のズレ）（20%）
            </div>
          </div>

          <div className={styles.axisCard}>
            <h3 className={styles.axisTitle}>リターン実績</h3>
            <p className={styles.axisText}>
              過去のパフォーマンス実績を評価します。リターンが高いほどスコアが高くなります。
            </p>
            <div className={styles.axisMetric}>
              使用指標: 1年リターン（40%）、3年リターン（60%）
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>カスタム重みづけ</h2>
        <p className={styles.text}>
          ログインユーザーは、5つの評価軸の重みを自由にカスタマイズできます。
          「カスタム」タブから設定画面を開き、各指標の重要度を0-100で設定してください。
        </p>
        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>設定例</div>
          <div className={styles.highlightText}>
            配当力: 40、コスト効率: 30、安定性: 20、取引規模: 10、リターン実績: 0
            のように設定すると、配当と低コストを重視したランキングが表示されます。
          </div>
        </div>
      </section>

      <nav className={styles.guideNav}>
        <div className={styles.guideNavLinks}>
          <Link to={ROUTES.GUIDE} className={styles.guideNavLink}>← 概要</Link>
          <Link to={ROUTES.GUIDE_SEARCH} className={styles.guideNavLink}>銘柄を探す →</Link>
        </div>
        <Link to={ROUTES.HOME} className={styles.guideNavCta}>この機能を使ってみる →</Link>
      </nav>
    </div>
  )
}
