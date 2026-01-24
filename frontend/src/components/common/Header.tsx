/** Header component */
import { Link, useLocation } from 'react-router-dom';
import { ROUTES } from '../../utils';
import styles from './Header.module.css';

export function Header() {
  const location = useLocation();

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
        </nav>
      </div>
    </header>
  );
}
