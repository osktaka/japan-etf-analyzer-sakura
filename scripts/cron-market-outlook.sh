#!/bin/bash
set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

# 1. market-outlookレポート生成
# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

setsid --wait claude -p "/market-outlook" \
  --allowedTools "WebSearch WebFetch Bash Read Write Edit Glob Grep Task Skill" \
  > "$LOGDIR/market-outlook-${TIMESTAMP}.log" 2>&1
STEP1_EXIT=$?

sleep 3

# 2. X投稿文生成（レポート読み→Markdown書き出しのみ）
setsid --wait claude -p "最新のmarket-outlookのレポートをもとにX用の投稿を書いて。market-outlookのレポート内容から最適なポイントを抽出して。X投稿用に最適な文章を構成して。1つの投稿は180文字程度にまとめて。1つの投稿にまとまらなければ複数投稿を書いて。表題の右には「[テスト]」と付けて。出力はreports/tmp_x_posts.mdに書き出して。コンテキスト使用サイズを抑えるように最適な実行をして。" \
  --allowedTools "Read Write Glob Grep" \
  > "$LOGDIR/market-x-posts-${TIMESTAMP}.log" 2>&1
STEP2_EXIT=$?

# 終了コード: いずれかが失敗していれば1
if [ $STEP1_EXIT -ne 0 ] || [ $STEP2_EXIT -ne 0 ]; then
  exit 1
fi
