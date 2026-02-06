-- Migration: 007_add_index_parent_batch_log_id
-- Description: batch_logsテーブルのparent_batch_log_idにインデックスを追加（NOT INサブクエリのパフォーマンス向上）
-- Date: 2026-02-06

CREATE INDEX IF NOT EXISTS ix_batch_logs_parent_batch_log_id ON batch_logs(parent_batch_log_id);
