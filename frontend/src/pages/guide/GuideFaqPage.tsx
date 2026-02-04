/** Guide FAQ Page - Frequently asked questions */
import { SEOHead } from '../../components/common'
import styles from './GuidePage.module.css'

export function GuideFaqPage() {
  const faqs = [
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
      question: 'スコアはどのように計算されていますか？',
      answer:
        '5つの評価軸（配当力、コスト効率、安定性、取引規模、リターン実績）を数値化し、切り口ごとの重み付けで0-100のスコアに変換しています。例えば「配当収入」では配当力の重みが50%と高く設定されています。「バランス」は5軸を均等（各20%）に評価します。',
    },
    {
      question: '比較リストは保存されますか？',
      answer:
        '比較リストはブラウザのセッションストレージに保存されます。同じタブ内であればページ遷移しても保持されますが、タブやブラウザを閉じるとクリアされます。',
    },
    {
      question: 'お気に入りやポートフォリオのデータはどこに保存されますか？',
      answer:
        'お気に入りとポートフォリオのデータは、ログインユーザーごとにサーバーに保存されます。異なるデバイスやブラウザからログインしても、同じデータにアクセスできます。',
    },
    {
      question: 'アカウントを削除したい場合は？',
      answer:
        '現在、セルフサービスでのアカウント削除機能は提供していません。削除をご希望の場合は、お問い合わせください。',
    },
    {
      question: '表示されていない銘柄があります',
      answer:
        '東証に上場しているETFを対象としていますが、上場直後の銘柄や一部の特殊なETFは表示されない場合があります。また、上場廃止された銘柄は表示されません。',
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
    {
      question: '無料で使えますか？',
      answer:
        'はい、すべての機能を無料でご利用いただけます。アカウント登録も無料です。',
    },
  ]

  return (
    <div className={styles.page}>
      <SEOHead
        title="よくある質問 - Japan ETF Analyzer"
        description="Japan ETF Analyzerに関するよくある質問と回答をまとめました。ETFの基礎知識から機能の使い方まで解説します。"
      />

      <h1 className={styles.pageTitle}>よくある質問</h1>

      <p className={styles.text}>
        Japan ETF
        Analyzerに関するよくある質問をまとめました。お探しの回答が見つからない場合は、お問い合わせください。
      </p>

      <section className={styles.section}>
        <ul className={styles.faqList}>
          {faqs.map((faq, index) => (
            <li key={index} className={styles.faqItem}>
              <div className={styles.faqQuestion}>
                <span className={styles.faqBadge}>Q</span>
                {faq.question}
              </div>
              <div className={styles.faqAnswer}>{faq.answer}</div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
