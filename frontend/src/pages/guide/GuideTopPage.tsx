/** Guide Top Page - Overview and navigation */
import { Link } from 'react-router-dom'
import { SEOHead } from '../../components/common'
import { ROUTES } from '../../utils'
import styles from './GuidePage.module.css'

export function GuideTopPage() {
  return (
    <div className={styles.page}>
      <SEOHead
        title="使い方ガイド - Japan ETF Analyzer"
        description="Japan ETF Analyzerの使い方を解説します。銘柄検索、おすすめ銘柄、比較機能、マイページの活用方法を学びましょう。"
      />

      <h1 className={styles.pageTitle}>使い方ガイド</h1>

      <p className={styles.text}>
        Japan ETF
        Analyzerは、東証に上場するETF銘柄を検索・比較・分析できるWebアプリケーションです。
        このガイドでは、主要な機能の使い方を説明します。
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3つの特徴</h2>
        <div className={styles.featureGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>&#128200;</div>
            <h3 className={styles.featureTitle}>6つの切り口</h3>
            <p className={styles.featureText}>
              配当重視、低コスト、安定性など6つの視点からおすすめ銘柄を提案。
              目的に合った銘柄を見つけやすくします。
            </p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>&#128269;</div>
            <h3 className={styles.featureTitle}>多角的な検索</h3>
            <p className={styles.featureText}>
              カテゴリ、信託報酬、利回りなど複数の条件で銘柄を絞り込み。
              あなたの投資スタイルに合った銘柄を効率的に探せます。
            </p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>&#9878;</div>
            <h3 className={styles.featureTitle}>かんたん比較</h3>
            <p className={styles.featureText}>
              最大5銘柄を並べて比較。価格チャート、指標、特徴を一目で把握でき、
              投資判断をサポートします。
            </p>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>目次</h2>
        <div className={styles.navGrid}>
          <Link to={ROUTES.GUIDE_RECOMMEND} className={styles.navCard}>
            <div className={styles.navCardTitle}>おすすめ銘柄</div>
            <div className={styles.navCardText}>6つの切り口の詳細</div>
          </Link>
          <Link to={ROUTES.GUIDE_SEARCH} className={styles.navCard}>
            <div className={styles.navCardTitle}>銘柄を探す</div>
            <div className={styles.navCardText}>
              検索・フィルター機能の使い方
            </div>
          </Link>
          <Link to={ROUTES.GUIDE_COMPARE} className={styles.navCard}>
            <div className={styles.navCardTitle}>比較する</div>
            <div className={styles.navCardText}>銘柄比較機能の活用法</div>
          </Link>
          <Link to={ROUTES.GUIDE_MYPAGE} className={styles.navCard}>
            <div className={styles.navCardTitle}>マイページ活用</div>
            <div className={styles.navCardText}>
              お気に入り・ポートフォリオ管理
            </div>
          </Link>
          <Link to={ROUTES.GUIDE_FAQ} className={styles.navCard}>
            <div className={styles.navCardTitle}>よくある質問</div>
            <div className={styles.navCardText}>Q&A形式で疑問を解決</div>
          </Link>
        </div>
      </section>
    </div>
  )
}
