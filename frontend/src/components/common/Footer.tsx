/** Footer component */
import styles from './Footer.module.css'

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className="container">
        <p className={styles.copyright}>
          &copy; {new Date().getFullYear()} Japan ETF Analyzer
        </p>
        <p className={styles.disclaimer}>
          投資は自己責任で行ってください。本サイトの情報は投資の勧誘を目的としたものではありません。
        </p>
      </div>
    </footer>
  )
}
