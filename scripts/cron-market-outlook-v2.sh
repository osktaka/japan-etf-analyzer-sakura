#!/bin/bash
set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

# タイミング引数（am/pm）、未指定時は現在時刻で自動判定
TIMING="${1:-}"

# Docker起動確認
if ! docker compose ps --status running 2>/dev/null | grep -q "backend"; then
  echo "Error: backend container is not running. Start with: docker compose up -d"
  exit 1
fi

# 休場日チェック
# - 日曜: 常にスキップ
# - 土曜 pm: スキップ（東証も米国も新情報なし）
# - 土曜 am: 通す（米国金曜夜の結果がある）
# - 平日 祝日: スキップ
# - 平日 非祝日: 通す
SKIP_REASON=$(docker compose exec -T -e TIMING="$TIMING" backend python3 -c "
import os, sys
from datetime import date, datetime
import jpholiday

timing = os.environ.get('TIMING', '')
if not timing:
    timing = 'am' if datetime.now().hour < 12 else 'pm'

today = date.today()
wd = today.weekday()  # 0=Mon ... 6=Sun

if wd == 6:
    print('Sunday')
elif wd == 5 and timing == 'pm':
    print('Saturday PM')
elif wd < 5 and jpholiday.is_holiday(today):
    print('Holiday (' + jpholiday.is_holiday_name(today) + ')')
else:
    print('')
") || {
  echo "Error: Failed to check holiday status" >&2
  exit 1
}

if [ -n "$SKIP_REASON" ]; then
  echo "Skipped ($(date +%Y-%m-%d) ${TIMING:-auto}, reason: $SKIP_REASON)"
  exit 0
fi
echo "Running market-outlook-v2 ($(date +%Y-%m-%d) ${TIMING:-auto})"

# 1. market-outlook-v2レポート生成
# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

setsid --wait claude -p "/market-outlook-v2" \
  --allowedTools "WebSearch WebFetch Bash Read Write Edit Glob Grep Agent Skill" \
  > "$LOGDIR/market-outlook-v2-${TIMESTAMP}.log" 2>&1
STEP1_EXIT=$?

if [ $STEP1_EXIT -ne 0 ]; then
  echo "Step 1 failed (exit=$STEP1_EXIT), skipping steps 2-3" >&2
  exit 1
fi

sleep 3

# 2. X投稿文生成（スキル化）
setsid --wait claude -p "/market-x-draft" \
  --allowedTools "Read Write Glob" \
  > "$LOGDIR/market-x-draft-${TIMESTAMP}.log" 2>&1
STEP2_EXIT=$?

if [ $STEP2_EXIT -ne 0 ]; then
  echo "Step 2 failed (exit=$STEP2_EXIT), skipping step 3" >&2
  exit 1
fi

sleep 3

# 3. X投稿実行
setsid --wait claude -p "/x-publish --auto --production" \
  --allowedTools "Read Edit Bash Glob" \
  > "$LOGDIR/x-publish-${TIMESTAMP}.log" 2>&1
STEP3_EXIT=$?

if [ $STEP3_EXIT -ne 0 ]; then
  echo "Step 3 failed (exit=$STEP3_EXIT), posts saved in reports/tmp_x_posts_v2.md" >&2
  exit 1
fi
