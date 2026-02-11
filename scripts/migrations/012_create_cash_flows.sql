-- Migration: 012_create_cash_flows
-- Description: 入出金履歴テーブルを作成
-- Date: 2026-02-11

CREATE TABLE IF NOT EXISTS cash_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flow_type VARCHAR(10) NOT NULL,  -- 'deposit' or 'withdrawal'
    amount DECIMAL(12,2) NOT NULL,
    flow_date DATE NOT NULL,
    memo TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_cash_flows_user_id ON cash_flows(user_id);
CREATE INDEX IF NOT EXISTS ix_cash_flows_flow_date ON cash_flows(flow_date);
