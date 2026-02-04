/** Guide Compare Page - How to compare ETFs */
import { SEOHead } from '../../components/common'
import styles from './GuidePage.module.css'

export function GuideComparePage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="比較する - Japan ETF Analyzer"
        description="Japan ETF Analyzerの比較機能の使い方を解説します。最大5銘柄を選んで、チャートや指標を並べて比較できます。"
      />

      <h1 className={styles.pageTitle}>比較する</h1>

      <p className={styles.text}>
        比較機能を使えば、最大5銘柄を並べてチャートや指標を比較できます。
        気になる銘柄を選んで、投資判断に役立てましょう。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>使い方</h2>
        <ol className={styles.stepList}>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>銘柄を選択</div>
            <div className={styles.stepText}>
              トップページやおすすめ銘柄の各カードにある「比較に追加」ボタンをクリックします。
              または、銘柄詳細モーダルからも追加できます。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>比較リストを確認</div>
            <div className={styles.stepText}>
              画面右下に表示される比較リストで、選択中の銘柄を確認できます。
              ここで銘柄を削除することも可能です。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>比較ページへ移動</div>
            <div className={styles.stepText}>
              比較リストの「比較する」ボタンをクリックすると、比較ページに移動します。
              ヘッダーの「比較」リンクからもアクセスできます。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>チャート・指標を比較</div>
            <div className={styles.stepText}>
              価格推移チャートで値動きを比較し、下の比較表で各種指標を確認できます。
            </div>
          </li>
        </ol>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>比較できる情報</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>&#128200;</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>価格チャート</div>
              <div className={styles.listDescription}>
                1ヶ月〜20年の期間で価格推移を表示。「相対比較」で複数銘柄を重ねて比較、「個別」で銘柄ごとに表示できます。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>&#128176;</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>基本指標</div>
              <div className={styles.listDescription}>
                カテゴリ、市場価格、配当利回り、信託報酬、純資産総額、タグ。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>&#128202;</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>パフォーマンス</div>
              <div className={styles.listDescription}>
                1ヶ月、3ヶ月、6ヶ月、1年のリターンとボラティリティ。
              </div>
            </div>
          </li>
        </ul>
      </section>

      <div className={styles.highlightBox}>
        <div className={styles.highlightTitle}>ヒント</div>
        <div className={styles.highlightText}>
          比較リストは画面を閉じても保持されます。後で比較したい銘柄を先に選んでおくと便利です。
        </div>
      </div>
    </div>
  )
}
