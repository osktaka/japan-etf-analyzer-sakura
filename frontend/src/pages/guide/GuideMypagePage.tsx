/** Guide MyPage Page - How to use favorites and portfolio */
import { Link } from 'react-router-dom'
import { SEOHead } from '../../components/common'
import { ROUTES } from '../../utils'
import styles from './GuidePage.module.css'

export function GuideMypagePage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="マイページ活用 - Japan ETF Analyzer"
        description="Japan ETF Analyzerのマイページ機能を解説します。お気に入り登録、ポートフォリオ管理、取引記録の使い方を学びましょう。"
      />

      <h1 className={styles.pageTitle}>マイページ活用</h1>

      <p className={styles.text}>
        ログインすると利用できるマイページ機能では、お気に入り銘柄の管理や
        ポートフォリオ（保有銘柄の一覧と構成）のシミュレーションができます。
      </p>

      <div className={styles.highlightBox}>
        <div className={styles.highlightTitle}>ログインが必要です</div>
        <div className={styles.highlightText}>
          マイページ機能を利用するには、アカウント登録とログインが必要です。
          画面右上の「ログイン」から登録・ログインしてください。
          新規登録はログイン画面の「アカウント作成」から、ユーザーID・パスワードを設定して登録できます。
        </div>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>お気に入り機能</h2>
        <ol className={styles.stepList}>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>お気に入りに追加</div>
            <div className={styles.stepText}>
              各銘柄カードやテーブルの星アイコンをクリックすると、お気に入りに追加できます。
              詳細モーダルからも追加可能です。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>お気に入りで絞り込み</div>
            <div className={styles.stepText}>
              フィルターパネルの「お気に入り」ボタンで、
              お気に入り銘柄のみを表示できます。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>マイページで一覧確認</div>
            <div className={styles.stepText}>
              マイページの「お気に入り一覧」セクションで、登録銘柄とスコアを確認できます。
              切り口タブで表示するスコアを切り替え、ソートON/OFFでスコア順に並べ替えられます。
            </div>
          </li>
        </ol>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>ポートフォリオ機能</h2>
        <p className={styles.text}>
          仮想的な取引を記録して、ポートフォリオのシミュレーションができます。
          実際の資産管理としてではなく、投資計画の検討にご活用ください。
        </p>
        <ol className={styles.stepList}>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>取引を追加</div>
            <div className={styles.stepText}>
              マイページの「取引を追加」ボタンをクリックし、
              購入・売却の情報（銘柄、日付、数量、価格）を入力します。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>保有状況を確認</div>
            <div className={styles.stepText}>
              マイページの「ポートフォリオ」セクションで、保有銘柄一覧と
              評価額、損益を確認できます。サマリーで全体の資産状況も把握できます。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>取引履歴を確認</div>
            <div className={styles.stepText}>
              「取引履歴」ボタンで過去の取引記録を一覧表示。銘柄で絞り込むこともできます。
            </div>
          </li>
          <li className={styles.stepItem}>
            <div className={styles.stepTitle}>推移を分析</div>
            <div className={styles.stepText}>
              ポートフォリオ全体の評価額推移をチャートで確認できます。
            </div>
          </li>
        </ol>
        <div className={styles.highlightBox + ' ' + styles.warning}>
          <div className={styles.highlightTitle}>ご注意</div>
          <div className={styles.highlightText}>
            ポートフォリオ機能は投資シミュレーション用です。
            実際の証券口座とは連携しておらず、税金計算等には対応していません。
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>保有中で絞り込み</h2>
        <p className={styles.text}>
          フィルターパネルの「保有中」ボタンで、
          ポートフォリオに登録した保有銘柄のみを表示できます。
          保有銘柄の市場動向を素早く確認したいときに便利です。
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>カスタム重みづけ</h2>
        <p className={styles.text}>
          5つの評価軸（配当力、コスト効率、安定性、取引規模、リターン実績）の重みを
          自分好みにカスタマイズできます。マイページやトップページの「カスタムを編集」から設定画面を開き、
          各指標の重要度を調整してください。 詳しくは
          <Link to={ROUTES.GUIDE_RECOMMEND}>「おすすめ銘柄」ガイド</Link>
          をご覧ください。
        </p>
      </section>

      <nav className={styles.guideNav}>
        <div className={styles.guideNavLinks}>
          <Link to={ROUTES.GUIDE_COMPARE} className={styles.guideNavLink}>
            ← 比較する
          </Link>
          <Link to={ROUTES.GUIDE_FAQ} className={styles.guideNavLink}>
            よくある質問 →
          </Link>
        </div>
        <Link to={ROUTES.MYPAGE} className={styles.guideNavCta}>
          この機能を使ってみる →
        </Link>
      </nav>
    </div>
  )
}
