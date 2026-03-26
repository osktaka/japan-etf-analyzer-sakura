-- Migration: 014_create_notes
-- Description: ノート記事管理テーブルを作成
-- Date: 2026-03-26

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug VARCHAR(200) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    published_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_notes_status_published_at ON notes(status, published_at DESC);
