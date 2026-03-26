/** Notes API client */
import { apiClient } from './client'
import { ApiResponse } from './types'

export interface NoteListItem {
  slug: string
  title: string
  summary: string
  status: string
  published_at: string
  updated_at: string
  created_at: string
}

export interface Note extends NoteListItem {
  content: string
}

export interface NoteInput {
  slug: string
  title: string
  summary: string
  content: string
  status: string
  published_at: string
}

export const notesApi = {
  async getAll(): Promise<NoteListItem[]> {
    const response =
      await apiClient.get<ApiResponse<NoteListItem[]>>('/notes')
    return response.data.data
  },

  async getBySlug(slug: string): Promise<Note> {
    const response =
      await apiClient.get<ApiResponse<Note>>(`/notes/${slug}`)
    return response.data.data
  },

  async getBySlugAdmin(slug: string): Promise<Note> {
    const response =
      await apiClient.get<ApiResponse<Note>>(`/admin/notes/${slug}`)
    return response.data.data
  },

  async getAllAdmin(): Promise<NoteListItem[]> {
    const response =
      await apiClient.get<ApiResponse<NoteListItem[]>>('/admin/notes')
    return response.data.data
  },

  async create(data: NoteInput): Promise<Note> {
    const response =
      await apiClient.post<ApiResponse<Note>>('/admin/notes', data)
    return response.data.data
  },

  async update(slug: string, data: NoteInput): Promise<Note> {
    const response =
      await apiClient.put<ApiResponse<Note>>(`/admin/notes/${slug}`, data)
    return response.data.data
  },

  async remove(slug: string): Promise<void> {
    await apiClient.delete<ApiResponse<void>>(`/admin/notes/${slug}`)
  },
}

export default notesApi
