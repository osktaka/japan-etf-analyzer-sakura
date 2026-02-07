-- Migration: 009_add_momentum_to_metrics_history
-- Description: etf_metrics_historyテーブルに勢い関連カラムを追加
-- Date: 2026-02-07

ALTER TABLE etf_metrics_history ADD COLUMN momentum_label TEXT;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_1m FLOAT;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_3m FLOAT;
