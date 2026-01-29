/** Floating compare button component */
import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCompareList, useFavorites, usePortfolio } from '../../hooks'
import { searchETFs } from '../../api'
import { ROUTES } from '../../utils'
import styles from './CompareFloatingButton.module.css'

interface ETFInfo {
  code: string
  name: string
}

const EXCLUDED_STORAGE_KEY = 'etf-compare-excluded'

export function CompareFloatingButton() {
  const navigate = useNavigate()
  const { codes, count, clearAll } = useCompareList()
  const { isFavorite } = useFavorites()
  const { holdings } = usePortfolio()

  // 保有銘柄コードのSet
  const holdingCodes = useMemo(() => {
    return new Set(holdings.map((h) => h.etf_code))
  }, [holdings])
  const [etfNames, setETFNames] = useState<Map<string, string>>(new Map())
  const [showTooltip, setShowTooltip] = useState(false)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [excludedCodes, setExcludedCodes] = useState<Set<string>>(() => {
    try {
      const stored = sessionStorage.getItem(EXCLUDED_STORAGE_KEY)
      return stored ? new Set(JSON.parse(stored)) : new Set()
    } catch {
      return new Set()
    }
  })

  // sessionStorageに除外リストを保存
  useEffect(() => {
    sessionStorage.setItem(
      EXCLUDED_STORAGE_KEY,
      JSON.stringify([...excludedCodes])
    )
  }, [excludedCodes])

  // 有効件数の計算
  const activeCount = codes.filter((c) => !excludedCodes.has(c)).length

  // チェックボックストグル関数
  const handleExcludeToggle = (code: string) => {
    setExcludedCodes((prev) => {
      const next = new Set(prev)
      if (next.has(code)) {
        next.delete(code)
      } else {
        next.add(code)
      }
      return next
    })
  }

  // 枠外クリックでリストを閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        tooltipRef.current &&
        !tooltipRef.current.contains(event.target as Node)
      ) {
        setShowTooltip(false)
      }
    }

    if (showTooltip) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showTooltip])

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
            <div className={styles.tooltipHeader}>銘柄比較</div>
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
                  <span className={styles.tooltipCode}>{etf.code}</span>
                  <span className={styles.tooltipName}>{etf.name}</span>
                  {/* 比較チェックボックス */}
                  <label className={styles.compareCheckbox}>
                    <input
                      type="checkbox"
                      checked={!excludedCodes.has(etf.code)}
                      onChange={() => handleExcludeToggle(etf.code)}
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
    </div>
  )
}
