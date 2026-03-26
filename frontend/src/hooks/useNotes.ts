/** Notes hooks */
import { useCallback, useEffect, useState } from 'react'
import { notesApi, NoteListItem, Note } from '../api/notes'
import { useAuth } from './useAuth'

interface UseNotesReturn {
  notes: NoteListItem[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

interface UseNoteReturn {
  note: Note | null
  loading: boolean
  error: string | null
}

export function useNotes(): UseNotesReturn {
  const { isAdmin } = useAuth()
  const [notes, setNotes] = useState<NoteListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchNotes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = isAdmin
        ? await notesApi.getAllAdmin()
        : await notesApi.getAll()
      setNotes(data)
    } catch (err) {
      setError('ノート一覧の取得に失敗しました')
      console.error('Failed to fetch notes:', err)
    } finally {
      setLoading(false)
    }
  }, [isAdmin])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  return { notes, loading, error, refresh: fetchNotes }
}

export function useNote(slug: string): UseNoteReturn {
  const [note, setNote] = useState<Note | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) {
      setLoading(false)
      return
    }

    const fetchNote = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await notesApi.getBySlug(slug)
        setNote(data)
      } catch (err) {
        setError('記事の取得に失敗しました')
        console.error('Failed to fetch note:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchNote()
  }, [slug])

  return { note, loading, error }
}
