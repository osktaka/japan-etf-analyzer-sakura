/** Portfolio page component */
import { useState } from 'react'
import { PortfolioSummary, HoldingsList } from '../components/portfolio'
import { ETFDetailModal } from '../components/modal/ETFDetailModal'
import { usePortfolio } from '../hooks/usePortfolio'
import styles from './PortfolioPage.module.css'

export function PortfolioPage() {
  const { holdings, summary, isLoading, error, refresh } = usePortfolio()
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  const handleETFClick = (code: string) => {
    setSelectedCode(code)
  }

  const handleCloseModal = () => {
    setSelectedCode(null)
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>ポートフォリオ</h1>
        <button className={styles.refreshBtn} onClick={refresh}>
          更新
        </button>
      </div>

      {summary && <PortfolioSummary summary={summary} />}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>保有銘柄</h2>
        <HoldingsList
          holdings={holdings}
          isLoading={isLoading}
          error={error}
          onETFClick={handleETFClick}
        />
      </section>

      {selectedCode && (
        <ETFDetailModal code={selectedCode} onClose={handleCloseModal} />
      )}
    </div>
  )
}

export default PortfolioPage
