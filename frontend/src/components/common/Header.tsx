/** Header component */
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTES } from '../../utils'
import styles from './Header.module.css'

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, isAdmin, logout, isLoading } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const handleLogout = async () => {
    await logout()
    setIsMenuOpen(false)
    navigate(ROUTES.HOME)
  }

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false)
      }
    }

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isMenuOpen])

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
            トップ
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
                    to={ROUTES.MYPAGE}
                    className={`${styles.navLink} ${location.pathname === ROUTES.MYPAGE ? styles.active : ''}`}
                  >
                    マイページ
                  </Link>
                  {isAdmin && (
                    <Link
                      to={ROUTES.ADMIN}
                      className={`${styles.navLink} ${location.pathname === ROUTES.ADMIN ? styles.active : ''}`}
                    >
                      管理
                    </Link>
                  )}
                  <div className={styles.userMenuContainer} ref={menuRef}>
                    <button
                      className={styles.userMenuButton}
                      onClick={() => setIsMenuOpen(!isMenuOpen)}
                    >
                      {user?.username} {isMenuOpen ? '▲' : '▼'}
                    </button>
                    {isMenuOpen && (
                      <div className={styles.userMenuDropdown}>
                        <button
                          className={styles.userMenuOption}
                          onClick={handleLogout}
                        >
                          ログアウト
                        </button>
                      </div>
                    )}
                  </div>
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
