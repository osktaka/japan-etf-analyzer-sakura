/** Admin page component */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import { adminApi, BatchLog, StockSplit } from '../api/admin'
import { User } from '../api/types'
import styles from './AdminPage.module.css'

type Tab = 'system' | 'users' | 'splits'

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('system')
  const [batchLogs, setBatchLogs] = useState<BatchLog[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [stockSplits, setStockSplits] = useState<StockSplit[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      // 検出日時の降順でソート
      const sortedData = data.sort((a, b) => {
        return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      })
      setStockSplits(sortedData)
    } catch (err) {
      console.error('Failed to load stock splits:', err)
      setError('株式分割一覧の取得に失敗しました')
    }
  }, [])

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

  const handleSplitStatusUpdate = async (
    splitId: number,
    status: 'approved' | 'rejected'
  ) => {
    try {
      const updatedSplit = await adminApi.updateStockSplitStatus(splitId, status)
      setStockSplits((prev) =>
        prev.map((split) => (split.id === splitId ? updatedSplit : split))
      )
    } catch (err) {
      console.error('Failed to update stock split status:', err)
      setError('株式分割の更新に失敗しました')
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
            <th>検出日時</th>
            <th>銘柄コード</th>
            <th>分割日</th>
            <th>変動率</th>
            <th>分割比率</th>
            <th>状態</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {stockSplits.map((split) => (
            <tr key={split.id}>
              <td>{formatDateTime(split.detected_at)}</td>
              <td>{split.etf_code}</td>
              <td>{split.split_date}</td>
              <td>
                {split.change_percent !== null
                  ? `${split.change_percent.toFixed(2)}%`
                  : '-'}
              </td>
              <td>{split.ratio.toFixed(2)}</td>
              <td>
                <span
                  className={`${styles.badge} ${
                    split.status === 'pending'
                      ? styles.badgeRunning
                      : split.status === 'approved'
                        ? styles.badgeSuccess
                        : styles.badgeFailed
                  }`}
                >
                  {split.status === 'pending'
                    ? '承認待ち'
                    : split.status === 'approved'
                      ? '承認済み'
                      : '却下'}
                </span>
              </td>
              <td>
                {split.status === 'pending' && (
                  <div className={styles.buttonGroup}>
                    <button
                      className={`${styles.button} ${styles.buttonSuccess}`}
                      onClick={() => handleSplitStatusUpdate(split.id, 'approved')}
                    >
                      承認
                    </button>
                    <button
                      className={`${styles.button} ${styles.buttonDanger}`}
                      onClick={() => handleSplitStatusUpdate(split.id, 'rejected')}
                    >
                      却下
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>管理画面</h1>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'system' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('system')}
        >
          システム状態
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'users' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('users')}
        >
          ユーザー管理
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'splits' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('splits')}
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
    </div>
  )
}

export default AdminPage
