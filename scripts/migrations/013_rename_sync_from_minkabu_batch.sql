-- Migration: 013_rename_sync_from_minkabu_batch
-- Description: バッチ名をsync_dividend_from_minkabuからsync_from_minkabuに変更
-- Date: 2026-03-10

UPDATE batch_logs SET batch_name = 'sync_from_minkabu' WHERE batch_name = 'sync_dividend_from_minkabu';
