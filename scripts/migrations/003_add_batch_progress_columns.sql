-- Migration: 003_add_batch_progress_columns
-- Description: batch_logsテーブルに進捗管理・リトライ機能用のカラムを追加
-- Date: 2026-02-03

-- 最終ハートビート時刻（タイムアウト検出用）
ALTER TABLE batch_logs ADD COLUMN last_heartbeat DATETIME;

-- 処理対象の総件数
ALTER TABLE batch_logs ADD COLUMN total_count INTEGER DEFAULT 0;

-- 処理済み件数
ALTER TABLE batch_logs ADD COLUMN processed_count INTEGER DEFAULT 0;

-- 最後に処理した項目コード（再開ポイント）
ALTER TABLE batch_logs ADD COLUMN last_item_code VARCHAR(20);

-- リトライ元のバッチログID（親子関係）
ALTER TABLE batch_logs ADD COLUMN parent_batch_log_id INTEGER;

-- リトライ回数
ALTER TABLE batch_logs ADD COLUMN retry_count INTEGER DEFAULT 0;

-- インデックス作成（タイムアウト検出とリトライ対象検索の効率化）
CREATE INDEX IF NOT EXISTS ix_batch_logs_status_heartbeat ON batch_logs (status, last_heartbeat);
CREATE INDEX IF NOT EXISTS ix_batch_logs_parent ON batch_logs (parent_batch_log_id);
