/** Header component */
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ROUTES } from '../../utils'
import styles from './Header.module.css'

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, logout, isLoading } = useAuth()

  const handleLogout = async () => {
    await logout()
    navigate(ROUTES.HOME)
  }

  return (
    <header className={styles.header}>
      <div className={`container ${styles.container}`}>
        <Link to={ROUTES.HOME} className={styles.logo}>
          Japan ETF Analyzer
        </Link>
        <nav className={styles.nav}>
          <Link
            to={ROUTES.HOME}
            className={`${styles.navLink} ${location.pathname === ROUTES.HOME ? styles.active : ''}`}
          >
            ホーム
          </Link>
          <Link
            to={ROUTES.COMPARE}
            className={`${styles.navLink} ${location.pathname === ROUTES.COMPARE ? styles.active : ''}`}
          >
            比較
          </Link>
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <Link
                    to={ROUTES.PORTFOLIO}
                    className={`${styles.navLink} ${location.pathname === ROUTES.PORTFOLIO ? styles.active : ''}`}
                  >
                    ポートフォリオ
                  </Link>
                  <Link
                    to={ROUTES.MYPAGE}
                    className={`${styles.navLink} ${location.pathname === ROUTES.MYPAGE ? styles.active : ''}`}
                  >
                    マイページ
                  </Link>
                  <span className={styles.userInfo}>{user?.username}</span>
                  <button onClick={handleLogout} className={styles.logoutBtn}>
                    ログアウト
                  </button>
                </>
              ) : (
                <Link to={ROUTES.LOGIN} className={styles.loginBtn}>
                  ログイン
                </Link>
              )}
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
