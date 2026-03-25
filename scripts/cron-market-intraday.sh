#!/bin/bash
set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

# 場中マーケット観察 → X投稿
# 東証: 10:00, 12:00, 13:30, 15:00（月〜金）
# 米国: 0:00, 3:00（火〜土 = 米国月〜金の夜）
# 市場モード判定はスキル側で自動実行（tokyo/us/skip）

# 1. 場中観察投稿文生成
# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

setsid --wait claude -p "/market-intraday" \
  --allowedTools "WebSearch Bash Read Write Glob" \
  > "$LOGDIR/market-intraday-${TIMESTAMP}.log" 2>&1
STEP1_EXIT=$?

if [ $STEP1_EXIT -ne 0 ]; then
  echo "Step 1 failed (exit=$STEP1_EXIT)" >&2
  exit 1
fi

sleep 3

# 2. X投稿実行
setsid --wait claude -p "/x-publish --auto --production" \
  --allowedTools "Read Edit Bash Glob" \
  > "$LOGDIR/x-publish-intraday-${TIMESTAMP}.log" 2>&1
STEP2_EXIT=$?

if [ $STEP2_EXIT -ne 0 ]; then
  echo "Step 2 failed (exit=$STEP2_EXIT), posts saved in reports/tmp_x_posts_v2.md" >&2
  exit 1
fi
