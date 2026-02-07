-- Migration: 010_add_regression_rate_columns
-- Description: etf_metrics_historyテーブルに6M〜20Yの回帰率カラムを追加
-- Date: 2026-02-07

ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_6m FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_1y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_3y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_5y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_10y FLOAT NULL;
ALTER TABLE etf_metrics_history ADD COLUMN regression_rate_20y FLOAT NULL;
