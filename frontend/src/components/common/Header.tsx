/** Header component */
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { ROUTES } from '../../utils'
import styles from './Header.module.css'

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, isAdmin, logout, isLoading } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const mobileMenuRef = useRef<HTMLDivElement>(null)
  const hamburgerButtonRef = useRef<HTMLButtonElement>(null)

  const handleLogout = async () => {
    await logout()
    setIsMenuOpen(false)
    setIsMobileMenuOpen(false)
    navigate(ROUTES.HOME)
  }

  const closeMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(false)
  }, [])

  // デスクトップユーザーメニューの外部クリック検知
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

  // モバイルメニューの外部クリック検知
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      // ハンバーガーボタンのクリックは除外（ボタン自身のonClickで処理）
      if (
        hamburgerButtonRef.current &&
        hamburgerButtonRef.current.contains(target)
      ) {
        return
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(target)) {
        closeMobileMenu()
      }
    }

    if (isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isMobileMenuOpen, closeMobileMenu])

  // Escapeキーでモバイルメニューを閉じる
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeMobileMenu()
      }
    }

    if (isMobileMenuOpen) {
      document.addEventListener('keydown', handleEscapeKey)
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey)
    }
  }, [isMobileMenuOpen, closeMobileMenu])

  // ルート変更時にモバイルメニューを閉じる
  useEffect(() => {
    closeMobileMenu()
  }, [location.pathname, closeMobileMenu])

  // メニュー展開時のbodyスクロールロック
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isMobileMenuOpen])

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

        {/* ハンバーガーボタン（モバイル用） */}
        <button
          ref={hamburgerButtonRef}
          className={styles.hamburgerButton}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-expanded={isMobileMenuOpen}
          aria-controls="mobile-menu"
          aria-label={isMobileMenuOpen ? 'メニューを閉じる' : 'メニューを開く'}
        >
          <span className={styles.hamburgerLine} />
          <span className={styles.hamburgerLine} />
          <span className={styles.hamburgerLine} />
        </button>

        {/* オーバーレイ（モバイル用） */}
        <div
          className={`${styles.mobileOverlay} ${isMobileMenuOpen ? styles.active : ''}`}
          onClick={closeMobileMenu}
          aria-hidden="true"
        />

        {/* モバイルメニュー */}
        <nav
          id="mobile-menu"
          ref={mobileMenuRef}
          className={`${styles.mobileMenu} ${isMobileMenuOpen ? styles.active : ''}`}
          role="menu"
          aria-label="モバイルナビゲーション"
        >
          <Link
            to={ROUTES.HOME}
            className={`${styles.mobileNavLink} ${location.pathname === ROUTES.HOME ? styles.active : ''}`}
            role="menuitem"
            onClick={closeMobileMenu}
          >
            トップ
          </Link>
          <Link
            to={ROUTES.COMPARE}
            className={`${styles.mobileNavLink} ${location.pathname === ROUTES.COMPARE ? styles.active : ''}`}
            role="menuitem"
            onClick={closeMobileMenu}
          >
            銘柄比較
          </Link>
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <Link
                    to={ROUTES.MYPAGE}
                    className={`${styles.mobileNavLink} ${location.pathname === ROUTES.MYPAGE ? styles.active : ''}`}
                    role="menuitem"
                    onClick={closeMobileMenu}
                  >
                    マイページ
                  </Link>
                  {isAdmin && (
                    <Link
                      to={ROUTES.ADMIN}
                      className={`${styles.mobileNavLink} ${location.pathname === ROUTES.ADMIN ? styles.active : ''}`}
                      role="menuitem"
                      onClick={closeMobileMenu}
                    >
                      管理
                    </Link>
                  )}
                  {user && (
                    <div className={styles.mobileUserInfo}>
                      {user.username} でログイン中
                    </div>
                  )}
                  <button
                    className={styles.mobileLogoutBtn}
                    onClick={handleLogout}
                    role="menuitem"
                  >
                    ログアウト
                  </button>
                </>
              ) : (
                <Link
                  to={ROUTES.LOGIN}
                  className={styles.mobileLoginBtn}
                  role="menuitem"
                  onClick={closeMobileMenu}
                >
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
