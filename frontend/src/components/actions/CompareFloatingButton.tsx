/** Floating compare button component */
import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useCompareList, useFavorites, usePortfolio } from '../../hooks'
import { searchETFs } from '../../api'
import { ROUTES } from '../../utils'
import { ETFDetailModal } from '../modal'
import styles from './CompareFloatingButton.module.css'

interface ETFInfo {
  code: string
  name: string
}

export function CompareFloatingButton() {
  const navigate = useNavigate()
  const location = useLocation()
  const { codes, count, clearAll, toggleCode } = useCompareList()
  const { isFavorite, toggleFavorite } = useFavorites()
  const { holdings } = usePortfolio({ skipSummary: true })
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  // 保有銘柄コードのSet
  const holdingCodes = useMemo(() => {
    return new Set(holdings.map((h) => h.etf_code))
  }, [holdings])
  const [etfNames, setETFNames] = useState<Map<string, string>>(new Map())
  const [showTooltip, setShowTooltip] = useState(false)
  const tooltipRef = useRef<HTMLDivElement>(null)

  // 有効件数の計算
  const activeCount = codes.length

  // 枠外クリックでリストを閉じる（モーダル表示中は無効化）
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        tooltipRef.current &&
        !tooltipRef.current.contains(event.target as Node)
      ) {
        setShowTooltip(false)
      }
    }

    if (showTooltip && !selectedCode) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showTooltip, selectedCode])

  // 銘柄名を取得
  useEffect(() => {
    if (codes.length === 0) {
      setETFNames(new Map())
      return
    }

    const fetchNames = async () => {
      const result = await searchETFs({ favorite_codes: codes, limit: 10 })
      const nameMap = new Map<string, string>()
      result.items.forEach((item) => {
        nameMap.set(item.code, item.name)
      })
      setETFNames(nameMap)
    }

    fetchNames()
  }, [codes])

  // 管理画面では非表示（Hooksの後で早期リターン）
  if (location.pathname.startsWith('/admin')) {
    return null
  }

  const handleClick = () => {
    navigate(ROUTES.COMPARE)
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    clearAll()
  }

  const etfList: ETFInfo[] = codes.map((code) => ({
    code,
    name: etfNames.get(code) || '読み込み中...',
  }))

  return (
    <div className={styles.container}>
      {/* メイン比較ボタン */}
      <button
        className={`${styles.mainButton} ${activeCount > 0 ? styles.active : ''}`}
        onClick={handleClick}
        aria-label={`銘柄比較 (${count}件)`}
      >
        <svg
          className={styles.icon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          {/* チャート/分析アイコン */}
          <path d="M3 3v18h18" />
          <path d="M7 16l4-4 4 4 5-6" />
        </svg>
        <span className={styles.text}>銘柄比較</span>
        {activeCount > 0 && <span className={styles.badge}>{activeCount}</span>}
      </button>

      {/* 銘柄リストボタン */}
      <div className={styles.listButtonWrapper} ref={tooltipRef}>
        <button
          className={styles.listButton}
          onClick={() => setShowTooltip(!showTooltip)}
          aria-label="登録銘柄リスト"
        >
          <svg
            className={styles.smallIcon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
          </svg>
        </button>

        {/* ツールチップ */}
        {showTooltip && (
          <div className={styles.tooltip}>
            <div className={styles.tooltipHeader}>銘柄リスト</div>
            <ul className={styles.tooltipList}>
              {etfList.map((etf) => (
                <li key={etf.code} className={styles.tooltipItem}>
                  {/* お気に入りアイコン */}
                  <span
                    className={`${styles.favoriteIcon} ${holdingCodes.has(etf.code) ? styles.holding : ''}`}
                  >
                    {isFavorite(etf.code) ? (
                      <svg
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                      </svg>
                    ) : (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                      </svg>
                    )}
                  </span>
                  <span
                    className={styles.tooltipCode}
                    onClick={() => setSelectedCode(etf.code)}
                    style={{ cursor: 'pointer' }}
                  >
                    {etf.code}
                  </span>
                  <span
                    className={styles.tooltipName}
                    onClick={() => setSelectedCode(etf.code)}
                    style={{ cursor: 'pointer' }}
                  >
                    {etf.name}
                  </span>
                  {/* 比較チェックボックス */}
                  <label className={styles.compareCheckbox}>
                    <input
                      type="checkbox"
                      checked={true}
                      onChange={() => toggleCode(etf.code)}
                    />
                  </label>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* クリアボタン */}
      <button
        className={styles.clearButton}
        onClick={handleClear}
        aria-label="リストをクリア"
      >
        <svg
          className={styles.smallIcon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>

      {/* 銘柄詳細モーダル */}
      {selectedCode && (
        <ETFDetailModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
          isInCompare={codes.includes(selectedCode)}
          onCompareToggle={() => selectedCode && toggleCode(selectedCode)}
          isFavorite={isFavorite(selectedCode)}
          onFavoriteToggle={() => selectedCode && toggleFavorite(selectedCode)}
        />
      )}
    </div>
  )
}
