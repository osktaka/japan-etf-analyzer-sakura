#!/bin/bash
set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

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
setsid --wait claude -p "/x-publish --auto" \
  --allowedTools "Read Edit Bash Glob" \
  > "$LOGDIR/x-publish-${TIMESTAMP}.log" 2>&1
STEP3_EXIT=$?

if [ $STEP3_EXIT -ne 0 ]; then
  echo "Step 3 failed (exit=$STEP3_EXIT), posts saved in reports/tmp_x_posts_v2.md" >&2
  exit 1
fi
