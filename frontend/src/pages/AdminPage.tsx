/** Admin page component */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { adminApi, BatchLog, StockSplit } from '../api/admin'
import { User } from '../api/types'
import { ETFDetailModal } from '../components/modal/ETFDetailModal'
import styles from './AdminPage.module.css'

type Tab = 'system' | 'users' | 'splits'
type SortKey =
  | 'detected_at'
  | 'etf_code'
  | 'etf_name'
  | 'split_date'
  | 'change_percent'
type SortOrder = 'asc' | 'desc'

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  // URLからタブ状態を取得、なければ'system'
  const initialTab = (searchParams.get('tab') as Tab) || 'system'
  const [activeTab, setActiveTab] = useState<Tab>(initialTab)

  const [batchLogs, setBatchLogs] = useState<BatchLog[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [stockSplits, setStockSplits] = useState<StockSplit[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ソート状態
  const [sortKey, setSortKey] = useState<SortKey>('detected_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // モーダル用の選択銘柄コード
  const [selectedCode, setSelectedCode] = useState<string | null>(null)

  // 再計算処理中の管理
  const [recalculatingIds, setRecalculatingIds] = useState<Set<number>>(
    new Set()
  )
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const loadBatchLogs = useCallback(async () => {
    try {
      const data = await adminApi.getBatchLogs()
      setBatchLogs(data)
    } catch (err) {
      console.error('Failed to load batch logs:', err)
      setError('バッチログの取得に失敗しました')
    }
  }, [])

  const loadUsers = useCallback(async () => {
    try {
      const data = await adminApi.getUsers()
      setUsers(data)
    } catch (err) {
      console.error('Failed to load users:', err)
      setError('ユーザー一覧の取得に失敗しました')
    }
  }, [])

  const loadStockSplits = useCallback(async () => {
    try {
      const data = await adminApi.getStockSplits()
      setStockSplits(data)
    } catch (err) {
      console.error('Failed to load stock splits:', err)
      setError('株式分割一覧の取得に失敗しました')
    }
  }, [])

  // タブ変更時にURLも更新
  const handleTabChange = useCallback(
    (tab: Tab) => {
      setActiveTab(tab)
      setSearchParams({ tab })
    },
    [setSearchParams]
  )

  // ソートヘッダークリックのハンドラ
  const handleSortClick = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        // 同じキーの場合は順序をトグル
        setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        // 新しいキーの場合はそのキーで降順ソート
        setSortKey(key)
        setSortOrder('desc')
      }
    },
    [sortKey]
  )

  // ソート済みの株式分割データ
  const sortedStockSplits = useMemo(() => {
    const sorted = [...stockSplits]
    sorted.sort((a, b) => {
      let aVal: string | number | null = null
      let bVal: string | number | null = null

      switch (sortKey) {
        case 'detected_at':
          aVal = new Date(a.detected_at).getTime()
          bVal = new Date(b.detected_at).getTime()
          break
        case 'etf_code':
          aVal = a.etf_code
          bVal = b.etf_code
          break
        case 'etf_name':
          aVal = a.etf_name || ''
          bVal = b.etf_name || ''
          break
        case 'split_date':
          aVal = a.split_date
          bVal = b.split_date
          break
        case 'change_percent':
          aVal = a.change_percent ?? -Infinity
          bVal = b.change_percent ?? -Infinity
          break
      }

      if (aVal === null || bVal === null) return 0
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
      return 0
    })
    return sorted
  }, [stockSplits, sortKey, sortOrder])

  // ソートインジケータの取得
  const getSortIndicator = (key: SortKey): string => {
    if (sortKey !== key) return ''
    return sortOrder === 'asc' ? ' ▲' : ' ▼'
  }

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)
      if (activeTab === 'system') {
        await loadBatchLogs()
      } else if (activeTab === 'users') {
        await loadUsers()
      } else if (activeTab === 'splits') {
        await loadStockSplits()
      }
      setIsLoading(false)
    }
    loadData()
  }, [activeTab, loadBatchLogs, loadUsers, loadStockSplits])

  const handleAdminToggle = async (userId: number, newValue: boolean) => {
    try {
      const updatedUser = await adminApi.updateUserAdmin(userId, newValue)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updatedUser : u)))
    } catch (err) {
      console.error('Failed to update user admin status:', err)
      setError('管理者権限の更新に失敗しました')
    }
  }

  const handleToggleApplied = async (splitId: number, isApplied: boolean) => {
    try {
      const updatedSplit = await adminApi.toggleStockSplitApplied(
        splitId,
        isApplied
      )
      setStockSplits((prev) =>
        prev.map((split) => (split.id === splitId ? updatedSplit : split))
      )
    } catch (err) {
      console.error('Failed to toggle stock split applied status:', err)
      setError('株式分割の更新に失敗しました')
    }
  }

  const handleToggleChartApplied = async (
    splitId: number,
    isChartApplied: boolean
  ) => {
    try {
      const updatedSplit = await adminApi.toggleStockSplitChartApplied(
        splitId,
        isChartApplied
      )
      setStockSplits((prev) =>
        prev.map((split) => (split.id === splitId ? updatedSplit : split))
      )
    } catch (err) {
      console.error('Failed to toggle stock split chart applied status:', err)
      setError('株式分割の更新に失敗しました')
    }
  }

  const handleRecalculate = async (splitId: number) => {
    try {
      setRecalculatingIds((prev) => new Set(prev).add(splitId))
      const result = await adminApi.recalculatePerformanceCache(splitId)

      // Update stockSplits state to reflect needs_recalculation = false
      setStockSplits((prev) =>
        prev.map((split) =>
          split.id === splitId
            ? { ...split, needs_recalculation: false }
            : split
        )
      )

      setToastMessage(
        `ETF ${result.etf_code} のパフォーマンスキャッシュを再計算しました（${result.updated_periods.length}期間）`
      )
      setTimeout(() => setToastMessage(null), 3000)
    } catch (err) {
      console.error('Failed to recalculate performance cache:', err)
      setToastMessage('再計算に失敗しました')
      setTimeout(() => setToastMessage(null), 3000)
    } finally {
      setRecalculatingIds((prev) => {
        const newSet = new Set(prev)
        newSet.delete(splitId)
        return newSet
      })
    }
  }

  const formatDateTime = (dateStr: string | null): string => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('ja-JP', {
      timeZone: 'Asia/Tokyo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (
    startedAt: string | null,
    finishedAt: string | null
  ): string => {
    if (!startedAt || !finishedAt) return '-'
    const start = new Date(startedAt)
    const finish = new Date(finishedAt)
    const durationMs = finish.getTime() - start.getTime()

    // 負の値の場合はエラー表示
    if (durationMs < 0) return 'エラー'

    const totalSeconds = Math.floor(durationMs / 1000)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }

  const renderStatusBadge = (status: BatchLog['status']) => {
    const badgeClass =
      status === 'success'
        ? styles.badgeSuccess
        : status === 'failed'
          ? styles.badgeFailed
          : styles.badgeRunning
    const label =
      status === 'success' ? '成功' : status === 'failed' ? '失敗' : '実行中'
    return <span className={`${styles.badge} ${badgeClass}`}>{label}</span>
  }

  const renderSystemTab = () => {
    if (isLoading) {
      return <div className={styles.loading}>読み込み中...</div>
    }
    if (error) {
      return <div className={styles.error}>{error}</div>
    }
    if (batchLogs.length === 0) {
      return <div className={styles.empty}>バッチ実行履歴はありません</div>
    }
    return (
      <table className={styles.table}>
        <thead>
          <tr>
            <th>バッチ名</th>
            <th>状態</th>
            <th>開始日時</th>
            <th>終了日時</th>
            <th>処理時間</th>
            <th>エラーメッセージ</th>
          </tr>
        </thead>
        <tbody>
          {batchLogs.map((log) => (
            <tr key={log.id}>
              <td>{log.batch_name}</td>
              <td>{renderStatusBadge(log.status)}</td>
              <td>{formatDateTime(log.started_at)}</td>
              <td>{formatDateTime(log.finished_at)}</td>
              <td>{formatDuration(log.started_at, log.finished_at)}</td>
              <td>
                {log.error_message && (
                  <span className={styles.errorMessage}>
                    {log.error_message}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  const renderUsersTab = () => {
    if (isLoading) {
      return <div className={styles.loading}>読み込み中...</div>
    }
    if (error) {
      return <div className={styles.error}>{error}</div>
    }
    if (users.length === 0) {
      return <div className={styles.empty}>ユーザーが登録されていません</div>
    }
    return (
      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>メール</th>
            <th>ユーザー名</th>
            <th>管理者</th>
            <th>作成日時</th>
            <th>最終ログイン</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSelf = currentUser?.id === user.id
            return (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>{user.username}</td>
                <td>
                  <label className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={user.is_admin}
                      disabled={isSelf}
                      onChange={(e) =>
                        handleAdminToggle(user.id, e.target.checked)
                      }
                    />
                    <span className={styles.toggleSlider} />
                  </label>
                </td>
                <td>{formatDateTime(user.created_at)}</td>
                <td>
                  {user.last_login_at
                    ? formatDateTime(user.last_login_at)
                    : '-'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }

  const renderSplitsTab = () => {
    if (isLoading) {
      return <div className={styles.loading}>読み込み中...</div>
    }
    if (error) {
      return <div className={styles.error}>{error}</div>
    }
    if (stockSplits.length === 0) {
      return <div className={styles.empty}>株式分割の候補はありません</div>
    }
    return (
      <table className={styles.table}>
        <thead>
          <tr>
            <th
              className={styles.sortable}
              onClick={() => handleSortClick('detected_at')}
            >
              検出日時{getSortIndicator('detected_at')}
            </th>
            <th
              className={styles.sortable}
              onClick={() => handleSortClick('etf_code')}
            >
              銘柄コード{getSortIndicator('etf_code')}
            </th>
            <th
              className={styles.sortable}
              onClick={() => handleSortClick('etf_name')}
            >
              銘柄名{getSortIndicator('etf_name')}
            </th>
            <th
              className={styles.sortable}
              onClick={() => handleSortClick('split_date')}
            >
              分割日{getSortIndicator('split_date')}
            </th>
            <th
              className={styles.sortable}
              onClick={() => handleSortClick('change_percent')}
            >
              変動率{getSortIndicator('change_percent')}
            </th>
            <th>分割比率</th>
            <th>ポートフォリオ適用</th>
            <th>チャート適用</th>
            <th>再計算</th>
          </tr>
        </thead>
        <tbody>
          {sortedStockSplits.map((split) => (
            <tr
              key={split.id}
              className={styles.clickableRow}
              onClick={() => setSelectedCode(split.etf_code)}
            >
              <td>{formatDateTime(split.detected_at)}</td>
              <td>{split.etf_code}</td>
              <td>{split.etf_name || '-'}</td>
              <td>{split.split_date}</td>
              <td>
                {split.change_percent !== null
                  ? `${split.change_percent.toFixed(2)}%`
                  : '-'}
              </td>
              <td>{split.ratio.toFixed(2)}</td>
              <td>
                <label
                  className={styles.toggle}
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={split.is_applied}
                    onChange={(e) =>
                      handleToggleApplied(split.id, e.target.checked)
                    }
                  />
                  <span className={styles.toggleSlider} />
                </label>
              </td>
              <td>
                <label
                  className={styles.toggle}
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={split.is_chart_applied}
                    onChange={(e) =>
                      handleToggleChartApplied(split.id, e.target.checked)
                    }
                  />
                  <span className={styles.toggleSlider} />
                </label>
              </td>
              <td onClick={(e) => e.stopPropagation()}>
                <button
                  className={styles.recalculateButton}
                  onClick={() => handleRecalculate(split.id)}
                  disabled={
                    recalculatingIds.has(split.id) || !split.needs_recalculation
                  }
                >
                  {recalculatingIds.has(split.id)
                    ? '処理中...'
                    : split.needs_recalculation
                      ? '実行'
                      : '済み'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  return (
    <div className={styles.container}>
      {/* Toast notification */}
      {toastMessage && <div className={styles.toast}>{toastMessage}</div>}

      <div className={styles.header}>
        <h1 className={styles.title}>管理画面</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'system' ? styles.tabActive : ''}`}
          onClick={() => handleTabChange('system')}
        >
          システム状態
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'users' ? styles.tabActive : ''}`}
          onClick={() => handleTabChange('users')}
        >
          ユーザー管理
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'splits' ? styles.tabActive : ''}`}
          onClick={() => handleTabChange('splits')}
        >
          株式分割
        </button>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          {activeTab === 'system'
            ? 'バッチ実行履歴'
            : activeTab === 'users'
              ? 'ユーザー一覧'
              : '株式分割候補'}
        </h2>
        {activeTab === 'system'
          ? renderSystemTab()
          : activeTab === 'users'
            ? renderUsersTab()
            : renderSplitsTab()}
      </section>

      {/* ETF詳細モーダル */}
      <ETFDetailModal
        code={selectedCode}
        onClose={() => setSelectedCode(null)}
      />
    </div>
  )
}

export default AdminPage
