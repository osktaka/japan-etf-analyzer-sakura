-- Migration: 008_add_momentum_label
-- Description: etfsテーブルにモメンタムラベルカラムを追加
-- Date: 2026-02-07

ALTER TABLE etfs ADD COLUMN momentum_label TEXT;
