/** Guide Sidebar component with navigation */
import { NavLink } from 'react-router-dom'
import { ROUTES } from '../../utils'
import styles from './GuideLayout.module.css'

const navItems = [
  { to: ROUTES.GUIDE, label: '概要', end: true },
  { to: ROUTES.GUIDE_RECOMMEND, label: 'おすすめ銘柄' },
  { to: ROUTES.GUIDE_SEARCH, label: '銘柄を探す' },
  { to: ROUTES.GUIDE_TAGS, label: 'タグで探す' },
  { to: ROUTES.GUIDE_COMPARE, label: '比較する' },
  { to: ROUTES.GUIDE_MYPAGE, label: 'マイページ活用' },
  { to: ROUTES.GUIDE_FAQ, label: 'よくある質問' },
]

export function GuideSidebar() {
  return (
    <nav className={styles.sidebar} aria-label="ガイドナビゲーション">
      <ul className={styles.navList}>
        {navItems.map((item) => (
          <li key={item.to} className={styles.navItem}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.active : ''}`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
