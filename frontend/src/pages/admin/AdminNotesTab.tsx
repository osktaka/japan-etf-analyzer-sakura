/** Admin Notes Tab component */
import { useState, useCallback, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { notesApi, NoteListItem, NoteInput } from '../../api/notes'
import styles from './AdminNotesTab.module.css'

type View = 'list' | 'create' | 'edit'

const EMPTY_FORM: NoteInput = {
  slug: '',
  title: '',
  summary: '',
  content: '',
  status: 'draft',
  published_at: new Date().toISOString().slice(0, 16),
}

/** Convert title to URL-safe slug */
function toSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim()
}

/** Format date for display */
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AdminNotesTab() {
  const [view, setView] = useState<View>('list')
  const [notes, setNotes] = useState<NoteListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<NoteInput>(EMPTY_FORM)
  const [editSlug, setEditSlug] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)

  const loadNotes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await notesApi.getAllAdmin()
      setNotes(data)
    } catch {
      setError('ノート一覧の取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadNotes()
  }, [loadNotes])

  const handleCreate = useCallback(() => {
    setForm(EMPTY_FORM)
    setEditSlug(null)
    setShowPreview(false)
    setView('create')
  }, [])

  const handleEdit = useCallback(async (slug: string) => {
    setLoading(true)
    try {
      const note = await notesApi.getBySlugAdmin(slug)
      setForm({
        slug: note.slug,
        title: note.title,
        summary: note.summary,
        content: note.content,
        status: note.status,
        published_at: note.published_at?.slice(0, 16) || '',
      })
      setEditSlug(slug)
      setShowPreview(false)
      setView('edit')
    } catch {
      setError('記事の取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleBack = useCallback(() => {
    setView('list')
    setError(null)
  }, [])

  const handleSubmit = useCallback(async () => {
    setSaving(true)
    setError(null)
    try {
      if (editSlug) {
        await notesApi.update(editSlug, form)
      } else {
        await notesApi.create(form)
      }
      await loadNotes()
      setView('list')
    } catch {
      setError(editSlug ? '記事の更新に失敗しました' : '記事の作成に失敗しました')
    } finally {
      setSaving(false)
    }
  }, [editSlug, form, loadNotes])

  const handleDelete = useCallback(async () => {
    if (!editSlug) return
    if (!window.confirm('この記事を削除しますか？')) return
    try {
      await notesApi.remove(editSlug)
      await loadNotes()
      setView('list')
    } catch {
      setError('記事の削除に失敗しました')
    }
  }, [editSlug, loadNotes])

  const updateField = useCallback(
    (field: keyof NoteInput, value: string) => {
      setForm((prev) => {
        const updated = { ...prev, [field]: value }
        // Auto-generate slug from title when creating
        if (field === 'title' && !editSlug) {
          updated.slug = toSlug(value)
        }
        return updated
      })
    },
    [editSlug]
  )

  if (view === 'list') {
    return (
      <NotesList
        notes={notes}
        loading={loading}
        error={error}
        onCreate={handleCreate}
        onEdit={handleEdit}
      />
    )
  }

  return (
    <NoteForm
      form={form}
      isEdit={view === 'edit'}
      saving={saving}
      error={error}
      showPreview={showPreview}
      onTogglePreview={() => setShowPreview((p) => !p)}
      onUpdateField={updateField}
      onSubmit={handleSubmit}
      onDelete={view === 'edit' ? handleDelete : undefined}
      onBack={handleBack}
    />
  )
}

/** Notes list sub-component */
function NotesList({
  notes,
  loading,
  error,
  onCreate,
  onEdit,
}: {
  notes: NoteListItem[]
  loading: boolean
  error: string | null
  onCreate: () => void
  onEdit: (slug: string) => void
}) {
  if (loading) {
    return <div className={styles.loading}>読み込み中...</div>
  }
  if (error) {
    return <div className={styles.error}>{error}</div>
  }

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <span>{notes.length}件の記事</span>
        <button className={styles.createButton} onClick={onCreate}>
          新規作成
        </button>
      </div>
      {notes.length === 0 ? (
        <div className={styles.empty}>記事がありません</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>状態</th>
              <th>公開日</th>
              <th>タイトル</th>
              <th>slug</th>
            </tr>
          </thead>
          <tbody>
            {notes.map((note) => (
              <tr
                key={note.slug}
                className={styles.clickableRow}
                onClick={() => onEdit(note.slug)}
              >
                <td>
                  <span
                    className={`${styles.badge} ${
                      note.status === 'published'
                        ? styles.badgePublished
                        : styles.badgeDraft
                    }`}
                  >
                    {note.status === 'published' ? '公開' : '下書き'}
                  </span>
                </td>
                <td>{formatDate(note.published_at)}</td>
                <td>{note.title}</td>
                <td>{note.slug}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/** Note form sub-component */
function NoteForm({
  form,
  isEdit,
  saving,
  error,
  showPreview,
  onTogglePreview,
  onUpdateField,
  onSubmit,
  onDelete,
  onBack,
}: {
  form: NoteInput
  isEdit: boolean
  saving: boolean
  error: string | null
  showPreview: boolean
  onTogglePreview: () => void
  onUpdateField: (field: keyof NoteInput, value: string) => void
  onSubmit: () => void
  onDelete?: () => void
  onBack: () => void
}) {
  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <button className={styles.backButton} onClick={onBack}>
          &larr; 一覧に戻る
        </button>
        <span>{isEdit ? '記事を編集' : '新規記事を作成'}</span>
      </div>
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.form}>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>タイトル</label>
          <input
            className={styles.formInput}
            value={form.title}
            onChange={(e) => onUpdateField('title', e.target.value)}
            placeholder="記事タイトル"
          />
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Slug</label>
          <input
            className={styles.formInput}
            value={form.slug}
            onChange={(e) => onUpdateField('slug', e.target.value)}
            placeholder="url-safe-slug"
          />
          <span className={styles.slugHint}>
            URLに使用されます（例: /notes/your-slug）
          </span>
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>概要</label>
          <input
            className={styles.formInput}
            value={form.summary}
            onChange={(e) => onUpdateField('summary', e.target.value)}
            placeholder="記事の概要（一覧に表示されます）"
          />
        </div>
        <div className={styles.formRow}>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>ステータス</label>
            <select
              className={styles.formSelect}
              value={form.status}
              onChange={(e) => onUpdateField('status', e.target.value)}
            >
              <option value="draft">下書き</option>
              <option value="published">公開</option>
            </select>
          </div>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>公開日時</label>
            <input
              className={styles.formInput}
              type="datetime-local"
              value={form.published_at}
              onChange={(e) => onUpdateField('published_at', e.target.value)}
            />
          </div>
        </div>
        <div className={styles.formGroup}>
          <div className={styles.toolbar}>
            <label className={styles.formLabel}>本文（Markdown）</label>
            <button
              className={styles.previewToggle}
              onClick={onTogglePreview}
            >
              {showPreview ? 'エディタ表示' : 'プレビュー表示'}
            </button>
          </div>
          {showPreview ? (
            <div className={styles.preview}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {form.content || '*（本文が空です）*'}
              </ReactMarkdown>
            </div>
          ) : (
            <textarea
              className={styles.formTextarea}
              value={form.content}
              onChange={(e) => onUpdateField('content', e.target.value)}
              placeholder="Markdown形式で記事本文を入力"
            />
          )}
        </div>
        <div className={styles.formActions}>
          <button
            className={styles.submitButton}
            onClick={onSubmit}
            disabled={saving || !form.title || !form.slug || !form.summary || !form.content}
          >
            {saving ? '保存中...' : isEdit ? '更新' : '作成'}
          </button>
          {isEdit && onDelete && (
            <button className={styles.deleteButton} onClick={onDelete}>
              削除
            </button>
          )}
          <button className={styles.cancelButton} onClick={onBack}>
            キャンセル
          </button>
        </div>
      </div>
    </div>
  )
}

export default AdminNotesTab
