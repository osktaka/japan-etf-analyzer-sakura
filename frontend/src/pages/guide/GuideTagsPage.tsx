/** Guide Tags Page - Explanation of 49 tags in 6 categories */
import { SEOHead } from '../../components/common'
import styles from './GuidePage.module.css'

export function GuideTagsPage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="タグで探す - Japan ETF Analyzer"
        description="Japan ETF Analyzerの49タグ6カテゴリについて解説します。経済ニュースから銘柄を探す方法を学びましょう。"
      />

      <h1 className={styles.pageTitle}>タグで探す</h1>

      <p className={styles.text}>
        Japan ETF
        Analyzerでは、49タグ6カテゴリでETF銘柄を多角的に分類しています。
        経済ニュースを見たときに「この状況で有利な銘柄は?」と思ったら、
        タグを使って素早く探すことができます。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>6つのタグカテゴリ</h2>
        <div className={styles.perspectiveGrid}>
          <div className={styles.perspectiveCard} data-perspective="dividend">
            <h3 className={styles.perspectiveTitle}>業種 (9タグ)</h3>
            <p className={styles.perspectiveText}>
              銀行、商社、不動産、半導体、自動車、医薬品、通信、電力・ガス、海運など、
              セクター別に銘柄を分類。業種に特化した投資戦略に活用できます。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 銀行セクター、半導体関連、商社関連
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="low-cost">
            <h3 className={styles.perspectiveTitle}>テーマ (12タグ)</h3>
            <p className={styles.perspectiveText}>
              高配当、低コスト、ESG、レバレッジ、インバースなど、
              投資テーマや銘柄特性で分類。目的に合った銘柄を見つけやすくします。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 高配当、低コスト、ESG・環境、レバレッジ
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="stability">
            <h3 className={styles.perspectiveTitle}>地域 (8タグ)</h3>
            <p className={styles.perspectiveText}>
              日本、米国、先進国、新興国、中国、インド、ASEAN、欧州など、
              投資対象地域で分類。地理的な分散投資に役立ちます。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 日本株、米国株、新興国、インド
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="volume">
            <h3 className={styles.perspectiveTitle}>資産クラス (4タグ)</h3>
            <p className={styles.perspectiveText}>
              株式、債券、REIT、コモディティなど、資産クラスで分類。
              アセットアロケーションを考える際に便利です。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 株式、債券、REIT、コモディティ
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="growth">
            <h3 className={styles.perspectiveTitle}>経済情勢 (7タグ)</h3>
            <p className={styles.perspectiveText}>
              円安、円高、金利上昇、金利低下、インフレヘッジ、ディフェンシブ、景気敏感など、
              経済環境に応じた銘柄選びに活用できます。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 円安メリット、金利上昇メリット、インフレヘッジ
            </div>
          </div>

          <div className={styles.perspectiveCard} data-perspective="balance">
            <h3 className={styles.perspectiveTitle}>政策 (3タグ)</h3>
            <p className={styles.perspectiveText}>
              防衛、インフラ、半導体政策など、国策・政策テーマで分類。
              政策関連銘柄を効率的に探せます。
            </p>
            <div className={styles.perspectiveMetrics}>
              例: 防衛関連、インフラ、半導体政策
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>経済ニュースから銘柄を探す</h2>
        <p className={styles.text}>
          経済情勢タグを使えば、ニュースを見たときにすぐに関連銘柄を探せます。
        </p>

        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>「円安が進行」</div>
          <div className={styles.highlightText}>
            「円安メリット」タグで検索 →
            外貨建て資産ETF、輸出関連株ETFが見つかります。
            海外収益の円換算額が増加し、業績にプラスとなる銘柄を効率的に探せます。
          </div>
        </div>

        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>「金利が上昇」</div>
          <div className={styles.highlightText}>
            「金利上昇メリット」タグで検索 → 銀行セクターETFなどが見つかります。
            金利上昇局面で利ざやが拡大する金融銘柄を素早く特定できます。
          </div>
        </div>

        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>「インフレ懸念」</div>
          <div className={styles.highlightText}>
            「インフレヘッジ」タグで検索 →
            ゴールドETF、REIT、コモディティETFが見つかります。
            インフレに強い実物資産に連動する銘柄を探せます。
          </div>
        </div>

        <div className={styles.highlightBox}>
          <div className={styles.highlightTitle}>「景気後退懸念」</div>
          <div className={styles.highlightText}>
            「ディフェンシブ」タグで検索 →
            公益・生活必需品セクターETFなどが見つかります。
            景気に左右されにくい銘柄でポートフォリオを守れます。
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>タグの使い方</h2>
        <ul className={styles.list}>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>1</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>トップページでタグを選択</div>
              <div className={styles.listDescription}>
                「銘柄を探す」セクションのフィルターでタグを選択します。
                6カテゴリから目的に合ったタグを選んでください。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>2</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>複数タグで幅広く検索</div>
              <div className={styles.listDescription}>
                複数のタグを選択すると、いずれかのタグを持つ銘柄が表示されます。
                例: 「高配当」+「低コスト」で、高配当または低コストのETFを検索。
              </div>
            </div>
          </li>
          <li className={styles.listItem}>
            <span className={styles.listIcon}>3</span>
            <div className={styles.listContent}>
              <div className={styles.listTitle}>カテゴリと組み合わせ</div>
              <div className={styles.listDescription}>
                タグはカテゴリフィルターと併用できます。
                カテゴリで大まかに絞り、タグで詳細条件を指定すると効果的です。
              </div>
            </div>
          </li>
        </ul>
      </section>
    </div>
  )
}
