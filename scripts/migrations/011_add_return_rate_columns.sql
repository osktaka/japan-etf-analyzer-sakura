-- Migration: 011_add_return_rate_columns
-- Description: etf_metrics_historyテーブルに株価上昇率カラムを追加
-- Date: 2026-02-07

ALTER TABLE etf_metrics_history ADD COLUMN return_rate_1m FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_3m FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_6m FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_1y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_3y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_5y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_10y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN return_rate_20y FLOAT NULL;
