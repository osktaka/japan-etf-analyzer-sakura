/** Guide Momentum Page - Explanation of momentum evaluation method */
import { SEOHead } from '../../components/common'
import styles from './GuidePage.module.css'

const momentumCategories = [
  {
    name: '上昇加速',
    color: '#059669',
    condition: '1M・3Mともにプラス、比率 > 1.45',
    meaning: '直近の上昇が中期トレンドより強い。勢いが加速中',
  },
  {
    name: '上昇維持',
    color: '#10b981',
    condition: '1M・3Mともにプラス、0.55 ≤ 比率 ≤ 1.45',
    meaning: '安定した上昇トレンドが継続中',
  },
  {
    name: '上昇減速',
    color: '#6ee7b7',
    condition: '1M・3Mともにプラス、比率 < 0.55',
    meaning: '上昇中だが直近の勢いは鈍化。ピークの可能性',
  },
  {
    name: '反転上昇',
    color: '#2563eb',
    condition: '1Mプラス、3Mマイナス',
    meaning: '中期は下降だが直近で上向きに転換。トレンド転換の兆し',
  },
  {
    name: '失速',
    color: '#f59e0b',
    condition: '1Mマイナス、3Mプラス',
    meaning: '中期は上昇だが直近で勢いが失われている',
  },
  {
    name: '下降減速',
    color: '#fca5a5',
    condition: '1M・3Mともにマイナス、比率 < 0.55',
    meaning: '下降中だが直近の下落幅は縮小。底入れの兆候',
  },
  {
    name: '下降維持',
    color: '#ef4444',
    condition: '1M・3Mともにマイナス、0.55 ≤ 比率 ≤ 1.45',
    meaning: '安定した下降トレンドが継続中',
  },
  {
    name: '下降加速',
    color: '#dc2626',
    condition: '1M・3Mともにマイナス、比率 > 1.45',
    meaning: '直近の下落が中期トレンドより強い。下落加速中',
  },
] as const

export function GuideMomentumPage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="勢いの評価方法 - Japan ETF Analyzer"
        description="回帰直線を使ったETFのモメンタム分析。8つの勢いカテゴリの仕組みと計算方法を解説します。"
      />

      <h1 className={styles.pageTitle}>勢いの評価方法</h1>

      <p className={styles.text}>
        株価の勢い（モメンタム）を回帰直線で数値化し、1ヶ月（短期）と3ヶ月（中期）の年率化リターンの比率で8段階に分類しています。
        日々の値動きのノイズに影響されにくい、統計的なトレンド評価手法です。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>8つの勢いカテゴリ</h2>
        <div className={styles.perspectiveGrid}>
          {momentumCategories.map((cat) => (
            <div
              key={cat.name}
              className={styles.perspectiveCard}
              style={{ borderLeftColor: cat.color }}
            >
              <h3 className={styles.perspectiveTitle}>{cat.name}</h3>
              <p className={styles.perspectiveText}>{cat.condition}</p>
              <div className={styles.perspectiveMetrics}>{cat.meaning}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>回帰直線とは</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>1</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>最小二乗法によるフィッティング</div>
              <div className={styles.listDescription}>
                期間内の全終値データに最もフィットする直線を算出します（最小二乗法）。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>2</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>ノイズに強いトレンド把握</div>
              <div className={styles.listDescription}>
                単純な「期末-期初」の差分より、日々の変動ノイズに強くトレンドの方向を安定的に捉えられます。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>3</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>回帰上昇率の算出</div>
              <div className={styles.listDescription}>
                回帰上昇率 = (回帰直線の終了値 - 開始値) / 開始値 x 100（%）で算出します。
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>年率化と比率による比較</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>1</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>年率化で期間差を吸収</div>
              <div className={styles.listDescription}>
                異なる期間のリターンを同じスケールで比較するため年率化します。
                1M回帰上昇率 x 12 = 年率化1M、3M回帰上昇率 x 4 = 年率化3M。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>2</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>比率（ratio）で勢いを判定</div>
              <div className={styles.listDescription}>
                ratio = 年率化1M / 年率化3M で短期と中期の勢いを比較します。
              </div>
            </div>
          </li>
        </ul>
        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>閾値の意味</div>
          <div className={styles.highlightText}>
            ratio {'>'} 1.45 → 加速（直近の勢いが中期の1.45倍超）。
            ratio {'<'} 0.55 → 減速（直近の勢いが中期の55%未満）。
            その間（0.55〜1.45）→ 維持（短期と中期がほぼ同じペース）。
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>注意事項</h2>
        <div className={`${styles.highlightBox} ${styles.warning}`}>
          <div className={styles.highlightText}>
            モメンタム評価は過去の株価データに基づく統計的分析であり、将来の値動きを保証するものではありません。
            投資判断は他の指標や市場環境と合わせてご検討ください。
          </div>
        </div>
      </section>
    </div>
  )
}
