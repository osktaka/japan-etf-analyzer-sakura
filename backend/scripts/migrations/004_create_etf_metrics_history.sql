-- Migration: 004_create_etf_metrics_history
-- Description: 評価スコア項目の日次履歴保存テーブルを作成
-- Date: 2026-02-04

CREATE TABLE IF NOT EXISTS etf_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    etf_code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    dividend_yield NUMERIC(5, 2),
    expense_ratio NUMERIC(5, 3),
    total_assets NUMERIC(15, 0),
    deviation_rate NUMERIC(5, 2),
    return_1y FLOAT,
    return_3y FLOAT,
    volatility FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(etf_code, date)
);
CREATE INDEX IF NOT EXISTS ix_etf_metrics_history_etf_code ON etf_metrics_history (etf_code);
CREATE INDEX IF NOT EXISTS ix_etf_metrics_history_date ON etf_metrics_history (date);
