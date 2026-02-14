import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SEOHead } from '../components/common/SEOHead'
import { getNoteBySlug, isPublished } from '../content/notes'
import { useAuth } from '../hooks/useAuth'
import { ROUTES } from '../utils/constants'
import styles from './NoteDetailPage.module.css'

/** Note detail page */
export function NoteDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { isAdmin } = useAuth()
  const note = slug ? getNoteBySlug(slug, isAdmin) : undefined

  if (!note) {
    return (
      <div className={styles.container}>
        <div className={styles.notFound}>
          <h2>記事が見つかりません</h2>
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
        publishedTime={note.publishedAt}
        modifiedTime={note.updatedAt}
      />
      <Link to={ROUTES.NOTES} className={styles.backLink}>
        ← ノート一覧
      </Link>
      <article className={styles.article}>
        <header className={styles.header}>
          <h1 className={styles.articleTitle}>{note.title}</h1>
          <div className={styles.meta}>
            <time dateTime={note.publishedAt}>{note.publishedAt.slice(0, 10)}</time>
            {note.updatedAt && (
              <span className={styles.updated}>（更新: {note.updatedAt}）</span>
            )}
            {!isPublished(note.publishedAt) && (
              <span className={styles.unpublishedBadge}>未公開</span>
            )}
          </div>
        </header>
        <div className={styles.content}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {note.content}
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
            datePublished: note.publishedAt,
            ...(note.updatedAt && { dateModified: note.updatedAt }),
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
