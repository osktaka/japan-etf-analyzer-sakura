/** Admin page component */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import { adminApi, BatchLog } from '../api/admin'
import { User } from '../api/types'
import styles from './AdminPage.module.css'

type Tab = 'system' | 'users'

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('system')
  const [batchLogs, setBatchLogs] = useState<BatchLog[]>([])
  const [users, setUsers] = useState<User[]>([])
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

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)
      if (activeTab === 'system') {
        await loadBatchLogs()
      } else {
        await loadUsers()
      }
      setIsLoading(false)
    }
    loadData()
  }, [activeTab, loadBatchLogs, loadUsers])

  const handleAdminToggle = async (userId: number, newValue: boolean) => {
    try {
      const updatedUser = await adminApi.updateUserAdmin(userId, newValue)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updatedUser : u)))
    } catch (err) {
      console.error('Failed to update user admin status:', err)
      setError('管理者権限の更新に失敗しました')
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
                <td>{user.last_login_at ? formatDateTime(user.last_login_at) : '-'}</td>
              </tr>
            )
          })}
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
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          {activeTab === 'system' ? 'バッチ実行履歴' : 'ユーザー一覧'}
        </h2>
        {activeTab === 'system' ? renderSystemTab() : renderUsersTab()}
      </section>
    </div>
  )
}

export default AdminPage
