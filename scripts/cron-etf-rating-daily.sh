#!/bin/bash
# ============================================================================
# ETF Rating 日次評価バッチ
#
# 月〜木 18:00 / 金 18:15（祝日スキップ）に cron-batch.sh から呼び出される。
# 金曜のみ 18:15 にずらすのは daily_advisor_weekly (18:00) との並列を避けるため。
# Claude CLI で `/etf-rating all --send-mail` を起動し、スキル内部の Bash で
# `scripts/etf_rating_send_mail.py`（コンテナ内では ./backend/scripts→/app/scripts に
# マウント。payload は /app/reports/etf-rating/_payloads/ 配下の絶対パスで渡す）を
# 実行してメール送信する。
#
# 実送信は `ETF_RATING_MAIL_ENABLED=1` 設定下でのみ実行（既定は dry-run）。
#
# NOTE: timeout 値を変更する場合は .claude/skills/etf-rating/calc_params.json の
# timeout_sec.total も同期すること（SSOT 統一）。両者がズレるとスキル内部の
# Phase 進行判断と外側の強制 kill タイミングが不整合になる。
# ============================================================================

set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

# 多重起動防止: cron-batch.sh は通常 dispatch と catch-up sweep の両経路で
# `bash scripts/cron-etf-rating-daily.sh &` を run_batch を経由せず直接起動するため、
# flock 保護がない。両経路を相互排他にして API/メール二重送信を防ぐ。
# ロック名は他バッチ (run_batch の /tmp/cron-batch-<NAME>.lock) と同一規約。
LOCKFILE="/tmp/cron-batch-etf_rating_daily.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [etf_rating_daily] skip (locked)"
  exit 0
fi

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGFILE="$PROJECT_DIR/logs/etf_rating.log"

mkdir -p "$PROJECT_DIR/logs"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# --- 祝日チェック（土日は cron-batch.sh 側で除外済み） ---
# docker compose exec は高コストのため当日結果を /tmp にキャッシュし cron-batch.sh と共有する。
# sakura 側が当日先にキャッシュ済みなら追加 exec は 0 回。未生成時のみ 1 回問い合わせ atomic 書込。
# トップレベル実装のため local は使えない。
HOLIDAY_CACHE="/tmp/etf_jpholiday_$(TZ=Asia/Tokyo date +%Y%m%d).cache"
if [[ -f "$HOLIDAY_CACHE" ]]; then
  HOLIDAY_VAL="$(cat "$HOLIDAY_CACHE" 2>/dev/null)"
else
  HOLIDAY_VAL="$(docker compose exec -T backend python3 -c "
import jpholiday, zoneinfo
from datetime import datetime
JST = zoneinfo.ZoneInfo('Asia/Tokyo')
print('1' if jpholiday.is_holiday(datetime.now(JST).date()) else '0')
" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$HOLIDAY_VAL" == "0" || "$HOLIDAY_VAL" == "1" ]]; then
    printf '%s' "$HOLIDAY_VAL" > "${HOLIDAY_CACHE}.tmp.$$" && mv -f "${HOLIDAY_CACHE}.tmp.$$" "$HOLIDAY_CACHE"
  fi
fi
if [[ "$HOLIDAY_VAL" == "1" ]]; then
  log "Holiday detected ($(date +%Y-%m-%d)), skipping etf-rating."
  exit 0
fi

# --- Docker 起動確認 ---
if ! docker compose ps --status running 2>/dev/null | grep -q "backend"; then
  log "Error: backend container is not running. Start with: docker compose up -d"
  exit 1
fi

log "===== etf-rating daily start ($TIMESTAMP) ====="

# --- Claude CLI で /etf-rating all --send-mail を起動 ---
# - timeout 3600s (60分): Phase 0 共通スナップショット + 全銘柄評価 + メール送信
#   2026-05-22 のフル実行で Phase 0/1/2 に25分使い Phase 3 中にタイムアウトした
#   実績を踏まえ、30分→60分に延長（claude CLI の暴走対策上限としては維持）
# - --send-mail: スキル内部の Bash で etf_rating_send_mail.py を呼び出す
# - 入れ子セッション防止
unset CLAUDECODE

# --allowedTools の設計根拠:
# - Read/Write/Grep/Glob/Bash/Task/TaskOutput/Skill/WebSearch/WebFetch のみ許可
# - Edit は新規 .md / .json の Write で完結するため不要
# - AskUserQuestion は自動実行モード（cron）では選択肢なしで decisions.log にデフォルト記録するため不要
setsid --wait timeout 3600 claude -p "/etf-rating all --send-mail" \
  --allowedTools "Read Bash Skill WebSearch WebFetch Task TaskOutput Write Grep Glob" \
  >> "$LOGFILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
  log "Error: etf-rating timed out (3600s)"
  exit 1
fi

if [ $EXIT_CODE -ne 0 ]; then
  log "Warning: etf-rating exited with code $EXIT_CODE"
  # スキル内部でメール送信を fail-soft 扱いするため exit 0 で cron を止めない
  exit 0
fi

log "===== etf-rating daily done (exit=$EXIT_CODE) ====="
exit 0
