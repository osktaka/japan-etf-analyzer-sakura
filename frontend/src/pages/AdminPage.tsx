/** Admin page component */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { adminApi, BatchLog, StockSplit } from '../api/admin'
import { User } from '../api/types'
import { ETFDetailModal } from '../components/modal/ETFDetailModal'
import { AdminNotesTab } from './admin/AdminNotesTab'
import styles from './AdminPage.module.css'

type Tab = 'system' | 'users' | 'splits' | 'notes'
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

  // URLパラメータの変更を監視（ブラウザの戻る/進むボタン対応）
  useEffect(() => {
    const tabFromUrl = (searchParams.get('tab') as Tab) || 'system'
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl)
    }
  }, [searchParams, activeTab])

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
      } else if (activeTab === 'notes') {
        // Notes tab manages its own loading
      }
      setIsLoading(false)
    }
    loadData()
  }, [activeTab, loadBatchLogs, loadUsers, loadStockSplits])

  // systemタブでは10秒間隔でバッチログを自動更新
  useEffect(() => {
    if (activeTab !== 'system') return

    const intervalId = setInterval(() => {
      loadBatchLogs()
    }, 10000)

    return () => clearInterval(intervalId)
  }, [activeTab, loadBatchLogs])

  const handleAdminToggle = async (userId: number, newValue: boolean) => {
    try {
      const updatedUser = await adminApi.updateUserAdmin(userId, newValue)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updatedUser : u)))
    } catch (err) {
      console.error('Failed to update user admin status:', err)
      setError('管理者権限の更新に失敗しました')
    }
  }

  const handleResetPassword = async (
    userId: number,
    userDisplayName: string
  ) => {
    const confirmed = window.confirm(
      `${userDisplayName} のパスワードをリセットしますか？\nランダムな一時パスワードが発行され、画面に表示されます。`
    )
    if (!confirmed) return

    try {
      const temporaryPassword = await adminApi.resetPassword(userId)
      // 一時パスワードは再表示できないため、確実に控えてもらう
      window.alert(
        `${userDisplayName} の一時パスワード:\n\n${temporaryPassword}\n\n本人に安全に手渡してください（この画面を閉じると再表示できません）。`
      )
      setToastMessage('パスワードをリセットしました')
      setTimeout(() => setToastMessage(null), 3000)
    } catch (err) {
      console.error('Failed to reset password:', err)
      setToastMessage('パスワードのリセットに失敗しました')
      setTimeout(() => setToastMessage(null), 3000)
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
    if (!startedAt) return '-'
    const start = new Date(startedAt)
    // finishedAtがnullの場合は現在時刻を使用（処理中の経過時間表示）
    const finish = finishedAt ? new Date(finishedAt) : new Date()
    const durationMs = finish.getTime() - start.getTime()

    // 負の値の場合はエラー表示
    if (durationMs < 0) return 'エラー'

    const totalSeconds = Math.floor(durationMs / 1000)
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }

  const isTimedOut = (log: BatchLog): boolean => {
    if (log.status !== 'running' || !log.last_heartbeat) {
      return false
    }
    const heartbeatTime = new Date(log.last_heartbeat).getTime()
    const now = Date.now()
    const diffMinutes = (now - heartbeatTime) / (1000 * 60)
    return diffMinutes > 30
  }

  const renderStatusBadge = (log: BatchLog) => {
    const timedOut = isTimedOut(log)

    if (log.status === 'running') {
      return (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className={`${styles.badge} ${styles.badgeRunning}`}>
            実行中
          </span>
          {timedOut && (
            <span
              className={`${styles.badge} ${styles.badgeFailed}`}
              title="30分以上ハートビート更新なし"
            >
              タイムアウト
            </span>
          )}
        </div>
      )
    }

    const badgeClass =
      log.status === 'success' ? styles.badgeSuccess : styles.badgeFailed
    const label = log.status === 'success' ? '成功' : '失敗'
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
            <th>ID</th>
            <th>バッチ名</th>
            <th>状態</th>
            <th>進捗</th>
            <th>開始日時</th>
            <th>終了日時</th>
            <th>処理時間</th>
            <th>エラーメッセージ</th>
            <th>アクション</th>
          </tr>
        </thead>
        <tbody>
          {batchLogs.map((log) => (
            <tr key={log.id}>
              <td>
                <strong>{log.id}</strong>
              </td>
              <td>
                <div>
                  {log.batch_name}
                  {log.parent_batch_log_id && (
                    <div
                      style={{
                        fontSize: '12px',
                        color: '#666',
                        marginTop: '4px',
                      }}
                    >
                      リトライ: {log.retry_count}回目（親ID:{' '}
                      {log.parent_batch_log_id}）
                    </div>
                  )}
                </div>
              </td>
              <td>{renderStatusBadge(log)}</td>
              <td style={{ minWidth: '180px' }}>
                {log.total_count > 0 ? (
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <div
                      style={{
                        position: 'relative',
                        height: '16px',
                        width: '150px',
                        background: '#e0e0e0',
                        borderRadius: '4px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          position: 'absolute',
                          height: '100%',
                          background: '#4caf50',
                          width: `${(log.processed_count / log.total_count) * 100}%`,
                          transition: 'width 0.3s ease',
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 'bold',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {log.processed_count}/{log.total_count} (
                      {Math.round(
                        (log.processed_count / log.total_count) * 100
                      )}
                      %)
                      {log.last_item_code && (
                        <small
                          style={{
                            color: '#666',
                            fontSize: '11px',
                            marginLeft: '4px',
                          }}
                        >
                          {log.last_item_code}
                        </small>
                      )}
                    </span>
                  </div>
                ) : (
                  <span>-</span>
                )}
              </td>
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
              <td>-</td>
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
            <th>ユーザーID</th>
            <th>表示名</th>
            <th>管理者</th>
            <th>作成日時</th>
            <th>最終ログイン</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSelf = currentUser?.id === user.id
            return (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.user_id}</td>
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
                <td>
                  <button
                    className={styles.recalculateButton}
                    onClick={() =>
                      handleResetPassword(
                        user.id,
                        user.username || user.user_id
                      )
                    }
                    disabled={isSelf}
                  >
                    PWリセット
                  </button>
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
        <button
          className={`${styles.tab} ${activeTab === 'notes' ? styles.tabActive : ''}`}
          onClick={() => handleTabChange('notes')}
        >
          ノート
        </button>
      </div>

      {activeTab === 'notes' ? (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>ノート管理</h2>
          <AdminNotesTab />
        </section>
      ) : (
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
      )}

      {/* ETF詳細モーダル */}
      <ETFDetailModal
        code={selectedCode}
        onClose={() => setSelectedCode(null)}
      />
    </div>
  )
}

export default AdminPage
