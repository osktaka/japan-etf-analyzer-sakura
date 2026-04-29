-- Migration: 015_create_mechanical_rule_events
-- Description: 機械ルール発動イベント（毎日のタスク通知システム）
-- Date: 2026-04-29

CREATE TABLE IF NOT EXISTS mechanical_rule_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint VARCHAR(128) NOT NULL UNIQUE,
    occurred_on DATE NOT NULL,
    rule_kind VARCHAR(50) NOT NULL,
    etf_code VARCHAR(20),
    user_id VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    payload_json TEXT,
    notified BOOLEAN NOT NULL DEFAULT 0,
    notified_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_mechanical_rule_events_fingerprint
    ON mechanical_rule_events(fingerprint);

CREATE INDEX IF NOT EXISTS ix_mechanical_rule_events_occurred_on
    ON mechanical_rule_events(occurred_on);

CREATE INDEX IF NOT EXISTS ix_mechanical_rule_events_user_kind
    ON mechanical_rule_events(user_id, rule_kind);
