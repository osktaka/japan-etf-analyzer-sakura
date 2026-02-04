/** Guide Search Page - How to search ETFs */
import { SEOHead } from '../../components/common'
import styles from './GuidePage.module.css'

export function GuideSearchPage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="銘柄を探す - Japan ETF Analyzer"
        description="Japan ETF Analyzerの検索・フィルター機能の使い方を解説します。キーワード検索、カテゴリ絞り込み、並び替えの方法を学びましょう。"
      />

      <h1 className={styles.pageTitle}>銘柄を探す</h1>

      <p className={styles.text}>
        トップページの「銘柄を探す」セクションでは、様々な条件でETF銘柄を検索できます。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>キーワード検索</h2>
        <p className={styles.text}>
          検索ボックスにキーワードを入力すると、銘柄名や証券コードで検索できます。
          例えば「日経225」「TOPIX」「1306」などで検索可能です。
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>フィルター機能</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>1</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>カテゴリ</div>
              <div className={styles.listDescription}>
                国内株式、外国株式、債券、REITなどカテゴリで絞り込みます。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>2</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>タグ</div>
              <div className={styles.listDescription}>
                高配当、低コスト、人気などのタグで絞り込みます。複数選択可能です。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>3</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>保有中・お気に入り</div>
              <div className={styles.listDescription}>
                ログイン後、保有銘柄やお気に入り登録した銘柄のみに絞り込めます。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>4</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>銘柄比較</div>
              <div className={styles.listDescription}>
                比較リストに追加した銘柄のみを表示して確認できます。
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>表示切替</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>A</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>カード / 表</div>
              <div className={styles.listDescription}>
                カード表示は視覚的に見やすく、表表示は一覧性に優れます。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>B</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>銘柄スコア / 株価傾向</div>
              <div className={styles.listDescription}>
                表表示時に、銘柄スコア（5軸評価）と株価傾向（期間別リターン）を切り替えられます。
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>並び替え</h2>
        <p className={styles.text}>
          テーブル表示では、各列のヘッダーをクリックすると並び替えができます。
          もう一度クリックすると昇順/降順が切り替わります。
        </p>
        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>スコアモード</div>
          <div className={styles.highlightText}>
            切り口（配当重視、低コストなど）を選択すると、その観点でのスコアで並び替えできます。
            複数の指標を総合的に評価したランキングが表示されます。
          </div>
        </div>
      </section>
    </div>
  )
}
