import { Link } from 'react-router-dom'
import { SEOHead } from '../components/common/SEOHead'
import { useNotes } from '../hooks/useNotes'
import { ROUTES } from '../utils/constants'
import styles from './NotesPage.module.css'

/** Notes listing page */
export function NotesPage() {
  const { notes, loading, error } = useNotes()

  return (
    <div className={styles.container}>
      <SEOHead
        title="ノート"
        description="ETF投資に関する分析記事・市場解説・投資のヒントをお届けします"
        path="/notes"
      />
      <h2 className={styles.title}>ノート</h2>
      {loading && <div className={styles.loading}>読み込み中...</div>}
      {error && <div className={styles.error}>{error}</div>}
      {!loading && !error && (
        <div className={styles.noteList}>
          {notes.map((note) => (
            <Link
              key={note.slug}
              to={`${ROUTES.NOTES}/${note.slug}`}
              className={styles.noteCard}
            >
              <div className={styles.noteDate}>
                {note.published_at.slice(0, 10)}
                {note.status === 'draft' && (
                  <span className={styles.unpublishedBadge}>未公開</span>
                )}
              </div>
              <h3 className={styles.noteTitle}>{note.title}</h3>
              <p className={styles.noteSummary}>{note.summary}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
