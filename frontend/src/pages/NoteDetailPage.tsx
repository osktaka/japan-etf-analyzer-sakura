import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SEOHead } from '../components/common/SEOHead'
import { useNote } from '../hooks/useNotes'
import { ROUTES } from '../utils/constants'
import styles from './NoteDetailPage.module.css'

/** Remove leading h1 from markdown if it matches the title */
function stripLeadingTitle(content: string, title: string): string {
  const match = content.match(/^#\s+(.+)\n/)
  if (match && match[1].trim() === title.trim()) {
    return content.slice(match[0].length).trimStart()
  }
  return content
}

/** Note detail page */
export function NoteDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { note, loading, error } = useNote(slug ?? '')

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>読み込み中...</div>
      </div>
    )
  }

  if (error || !note) {
    return (
      <div className={styles.container}>
        <div className={styles.notFound}>
          <h2>{error || '記事が見つかりません'}</h2>
          <Link to={ROUTES.NOTES}>ノート一覧に戻る</Link>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <SEOHead
        title={note.title}
        description={note.summary}
        path={`/notes/${note.slug}`}
        type="article"
        publishedTime={note.published_at}
        modifiedTime={note.updated_at}
      />
      <Link to={ROUTES.NOTES} className={styles.backLink}>
        &larr; ノート一覧
      </Link>
      <article className={styles.article}>
        <header className={styles.header}>
          <h1 className={styles.articleTitle}>{note.title}</h1>
          <div className={styles.meta}>
            <time dateTime={note.published_at}>
              {note.published_at.slice(0, 10)}
            </time>
            {note.status === 'draft' && (
              <span className={styles.unpublishedBadge}>未公開</span>
            )}
          </div>
        </header>
        <div className={styles.content}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {stripLeadingTitle(note.content, note.title)}
          </ReactMarkdown>
        </div>
      </article>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: note.title,
            description: note.summary,
            datePublished: note.published_at,
            ...(note.updated_at && { dateModified: note.updated_at }),
            publisher: {
              '@type': 'Organization',
              name: 'Japan ETF Analyzer',
              url: 'https://kima3.net/japan-etf-analyzer',
            },
          }),
        }}
      />
    </div>
  )
}
