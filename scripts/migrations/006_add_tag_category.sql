-- Migration: 006_add_tag_category
-- Description: tagsテーブルにcategoryカラムを追加
-- Date: 2026-02-05

-- categoryカラムを追加（既存の場合はエラーになるがマイグレーション管理で重複実行されない）
ALTER TABLE tags ADD COLUMN category VARCHAR(20);
