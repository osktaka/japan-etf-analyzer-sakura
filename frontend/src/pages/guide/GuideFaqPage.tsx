/** Guide FAQ Page - Frequently asked questions */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { SEOHead } from '../../components/common'
import { ROUTES } from '../../utils'
import styles from './GuidePage.module.css'

type FaqCategory = {
  title: string
  items: { question: string; answer: string }[]
}

const faqCategories: FaqCategory[] = [
  {
    title: '基本情報',
    items: [
      {
        question: 'ETFとは何ですか？',
        answer:
          'ETF（Exchange Traded Fund）は、株式と同じように証券取引所で売買できる投資信託です。日経平均やTOPIXなどの指数に連動するように設計されており、1つのETFで分散投資ができます。',
      },
      {
        question: 'このサイトのデータはリアルタイムで反映されますか？',
        answer:
          'データは定期的に更新されますが、リアルタイムではありません。投資判断の際は、証券会社の情報もご確認ください。',
      },
      {
        question: '無料で使えますか？',
        answer:
          'はい、すべての機能を無料でご利用いただけます。アカウント登録も無料です。',
      },
      {
        question: 'スマートフォンでも使えますか？',
        answer:
          'はい、スマートフォンやタブレットでもご利用いただけます。画面サイズに応じてレイアウトが自動調整されます。',
      },
      {
        question: '投資アドバイスは受けられますか？',
        answer:
          'このサイトは情報提供のみを目的としており、投資アドバイスは行っていません。投資は自己責任で行い、必要に応じて専門家にご相談ください。',
      },
    ],
  },
  {
    title: '機能について',
    items: [
      {
        question: 'スコアはどのように計算されていますか？',
        answer:
          '5つの評価軸（配当力、コスト効率、安定性、取引規模、リターン実績）を数値化し、切り口ごとの重み付けで0-100のスコアに変換しています。例えば「配当収入」では配当力の重みが50%と高く設定されています。「バランス」は5軸を均等（各20%）に評価します。',
      },
      {
        question: '比較リストは保存されますか？',
        answer:
          '比較リストはブラウザに一時保存（セッションストレージ）されます。同じタブ内であればページ遷移しても保持されますが、タブやブラウザを閉じるとクリアされます。',
      },
      {
        question: '表示されていない銘柄があります',
        answer:
          '東証に上場しているETFを対象としていますが、上場直後の銘柄や一部の特殊なETFは表示されない場合があります。また、上場廃止された銘柄は表示されません。',
      },
    ],
  },
  {
    title: 'アカウント',
    items: [
      {
        question: 'お気に入りやポートフォリオのデータはどこに保存されますか？',
        answer:
          'お気に入りとポートフォリオのデータは、ログインユーザーごとにサーバーに保存されます。異なるデバイスやブラウザからログインしても、同じデータにアクセスできます。',
      },
      {
        question: 'アカウントを削除したい場合は？',
        answer:
          '現在、セルフサービスでのアカウント削除機能は提供していません。削除をご希望の場合は、X（旧Twitter）の @ETF_Analyzer にご連絡ください。',
      },
    ],
  },
]

export function GuideFaqPage() {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0)

  const toggleFaq = (index: number) =>
    setExpandedIndex((prev) => (prev === index ? null : index))

  const getGlobalIndex = (categoryIndex: number, itemIndex: number) =>
    faqCategories.slice(0, categoryIndex).reduce((sum, c) => sum + c.items.length, 0) + itemIndex

  return (
    <div className={styles.page}>
      <SEOHead
        title="よくある質問 - Japan ETF Analyzer"
        description="Japan ETF Analyzerに関するよくある質問と回答をまとめました。ETFの基礎知識から機能の使い方まで解説します。"
      />

      <h1 className={styles.pageTitle}>よくある質問</h1>

      <p className={styles.text}>
        Japan ETF
        Analyzerに関するよくある質問をまとめました。お探しの回答が見つからない場合は、
        <a href="https://x.com/ETF_Analyzer" target="_blank" rel="noopener noreferrer">
          X（旧Twitter）の @ETF_Analyzer
        </a>
        にお問い合わせください。
      </p>

      {faqCategories.map((category, categoryIndex) => (
        <section key={category.title} className={styles.section}>
          <h2 className={styles.sectionTitle}>{category.title}</h2>
          <ul className={styles.faqList}>
            {category.items.map((faq, itemIndex) => {
              const currentIndex = getGlobalIndex(categoryIndex, itemIndex)
              return (
                <li key={currentIndex} className={styles.faqItem}>
                  <div
                    className={styles.faqQuestion}
                    onClick={() => toggleFaq(currentIndex)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        toggleFaq(currentIndex)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-expanded={expandedIndex === currentIndex}
                  >
                    <span className={styles.faqQuestionContent}>
                      <span className={styles.faqBadge}>Q</span>
                      {faq.question}
                    </span>
                    <span
                      className={`${styles.faqToggle} ${expandedIndex === currentIndex ? styles.open : ''}`}
                    >
                      +
                    </span>
                  </div>
                  <div
                    className={`${styles.faqAnswerWrapper} ${expandedIndex === currentIndex ? styles.open : ''}`}
                  >
                    <div className={styles.faqAnswerInner}>
                      <div className={styles.faqAnswer}>
                        <span className={styles.faqAnswerBadge}>A</span>
                        <span>{faq.answer}</span>
                      </div>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      ))}

      <nav className={styles.guideNav}>
        <div className={styles.guideNavLinks}>
          <Link to={ROUTES.GUIDE_MYPAGE} className={styles.guideNavLink}>← マイページ活用</Link>
        </div>
        <Link to={ROUTES.GUIDE} className={styles.guideNavCta}>ガイドトップに戻る →</Link>
      </nav>
    </div>
  )
}
