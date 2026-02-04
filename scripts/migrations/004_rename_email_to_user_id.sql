-- Migration: 004_rename_email_to_user_id
-- Description: usersテーブルのemailカラムをuser_idにリネーム
-- Date: 2026-02-04

ALTER TABLE users RENAME COLUMN email TO user_id;
UPDATE users SET user_id = substr(user_id, 1, instr(user_id, '@') - 1) WHERE instr(user_id, '@') > 0;
DROP INDEX IF EXISTS ix_users_email;
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_user_id ON users (user_id);
