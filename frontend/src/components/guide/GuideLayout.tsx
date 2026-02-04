/** Guide Layout component - 2-column layout with sidebar */
import { Outlet } from 'react-router-dom'
import { GuideSidebar } from './GuideSidebar'
import styles from './GuideLayout.module.css'

export function GuideLayout() {
  return (
    <div className={styles.layout}>
      <GuideSidebar />
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
