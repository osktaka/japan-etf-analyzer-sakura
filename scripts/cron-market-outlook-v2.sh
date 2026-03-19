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

sleep 3

# 2. X投稿文生成（レポート読み→Markdown書き出しのみ）
# AM/PM判定（最新v2ファイル名で判定）
LATEST_V2=$(ls -t reports/market-outlook/*_v2.md 2>/dev/null | head -1)
if echo "$LATEST_V2" | grep -q "_pm_"; then
  # PM用プロンプト（東証終了後）
  XPOST_PROMPT='reports/market-outlook/ディレクトリから最新の_pm_v2.mdファイルを読んで、以下の方針でX投稿3本をreports/tmp_x_posts_v2.mdに書き出して。コンテキスト使用サイズを抑えるように最適な実行をして。

## PM投稿方針（東証終了後・3投稿構成）

### 投稿1: 【東証レビュー MM/DD】[テスト]
- 今日の東証の動きを端的にまとめる（160文字程度）
- 主要指数の動き、目立ったセクター、特徴的な値動きを簡潔に
- 動的タグ2〜3個（例: #日経平均 #東証 #ETF）

### 投稿2: 【朝の予想と結果】[テスト]
- AMレポートで出した予想と実際の結果を比較（160文字程度）
- 的中・外れを正直に共有、外れた場合は理由も簡潔に
- 動的タグ2〜3個

### 投稿3: 【明日の監視ポイント】[テスト]
- 明日以降に注目すべきポイント（160文字程度）
- 具体的な銘柄・指標・イベントを挙げる
- 動的タグ2〜3個

## 出力フォーマット
各投稿を---で区切り、Markdown形式で出力。MM/DDは実際の日付に置換すること。'
else
  # AM用プロンプト（米国市場終了後）
  XPOST_PROMPT='reports/market-outlook/ディレクトリから最新の_am_v2.mdファイルを読んで、以下の方針でX投稿3本をreports/tmp_x_posts_v2.mdに書き出して。コンテキスト使用サイズを抑えるように最適な実行をして。

## AM投稿方針（米国市場終了後・3投稿構成）

### 投稿1: 【昨夜の米国市場】[テスト]
- 昨夜の米国市場の動きを端的にまとめる（160文字程度）
- 主要指数・注目イベント・為替の動きを簡潔に
- 動的タグ2〜3個（例: #米国株 #SP500 #為替）

### 投稿2: 【今日の東証予想】[テスト]
- 今日の東証がどう動くか予想（160文字程度）
- 予想の自信度（高/中/低）と根拠を正直に開示
- 動的タグ2〜3個

### 投稿3: 【今日の監視ポイント】[テスト]
- 今日注目すべき具体的なポイント（160文字程度）
- 具体的な銘柄・指標・イベントを挙げる
- 動的タグ2〜3個

## 出力フォーマット
各投稿を---で区切り、Markdown形式で出力。MM/DDは実際の日付に置換すること。'
fi

setsid --wait claude -p "$XPOST_PROMPT" \
  --allowedTools "Read Write Glob Grep" \
  > "$LOGDIR/market-x-posts-v2-${TIMESTAMP}.log" 2>&1
STEP2_EXIT=$?

# 終了コード: いずれかが失敗していれば1
if [ $STEP1_EXIT -ne 0 ] || [ $STEP2_EXIT -ne 0 ]; then
  exit 1
fi
