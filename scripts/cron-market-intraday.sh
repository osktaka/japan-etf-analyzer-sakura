#!/bin/bash
set -uo pipefail

# 場中マーケット観察 → X投稿
# cronは30分おき（*/30 * * * 1-6）で実行し、本スクリプトで時刻判定する
#
# 東証: 10:00, 12:00, 13:30, 15:00（月〜金）
# 米国: 22:00（プレマーケット、月〜金）, 0:00, 3:00（火〜土 = 米国月〜金の夜）
# 祝日判定はスキル側のCP1バリデーションで対応（年10-15回程度の起動は許容）
#
# オプション:
#   --now        時刻判定をスキップして即時実行
#   --at HH:MM   指定時刻として実行（例: --at 10:00）
#   --dry-run    判定結果のみ表示（claude CLIを起動しない）
#   --no-publish 投稿文生成のみ（x-publishをスキップ）

# --- オプション解析 ---
FORCE_NOW=false
FAKE_TIME=""
DRY_RUN=false
NO_PUBLISH=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --now)
      FORCE_NOW=true; shift ;;
    --at)
      FAKE_TIME="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    --no-publish)
      NO_PUBLISH=true; shift ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --now          時刻判定をスキップして即時実行"
      echo "  --at HH:MM    指定時刻として判定・実行（例: --at 10:00）"
      echo "  --dry-run      判定結果のみ表示（claude CLIを起動しない）"
      echo "  --no-publish   投稿文生成のみ（x-publishをスキップ）"
      echo "  -h, --help     このヘルプを表示"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- 時刻判定 ---
if [[ -n "$FAKE_TIME" ]]; then
  NOW="$FAKE_TIME"
  DOW=$(TZ=Asia/Tokyo date +%u)
  echo "[info] 時刻偽装: $NOW (dow=$DOW)" >&2
elif [[ "$FORCE_NOW" == true ]]; then
  NOW="FORCE"
  DOW=$(TZ=Asia/Tokyo date +%u)
  echo "[info] 即時実行モード" >&2
else
  HOUR=$(TZ=Asia/Tokyo date +%H)
  MIN=$(TZ=Asia/Tokyo date +%M)
  DOW=$(TZ=Asia/Tokyo date +%u)  # 1=月〜7=日
  NOW="${HOUR}:${MIN}"
fi

MARKET=""
if [[ "$NOW" == "FORCE" ]]; then
  MARKET="force"
else
  case "$NOW" in
    10:00|12:00|13:30|15:00)
      if [[ $DOW -ge 1 && $DOW -le 5 ]]; then
        MARKET="tokyo"
      fi ;;
    22:00)
      if [[ $DOW -ge 1 && $DOW -le 5 ]]; then
        MARKET="us"
      fi ;;
    00:00|03:00)
      if [[ $DOW -ge 2 && $DOW -le 6 ]]; then
        MARKET="us"
      fi ;;
  esac
fi

if [[ -z "$MARKET" ]]; then
  [[ "$DRY_RUN" == true ]] && echo "[dry-run] $NOW (dow=$DOW) → skip" >&2
  exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] $NOW (dow=$DOW) → RUN ($MARKET)" >&2
  exit 0
fi

# --- ここから先は実行対象の時刻のみ ---
PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

# 1. 場中観察投稿文生成
# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

# --now 実行時はファイル名を tmp_x_posts_v2_now.md にする
# それ以外は NOW (HH:MM) から HHMM を生成（FAKE_TIME/通常時刻の両方に対応）
if [[ "$FORCE_NOW" == true ]]; then
  INTRADAY_PROMPT="/market-intraday （出力ファイル名はtmp_x_posts_v2_now.mdにすること）"
  TARGET_FILE="reports/tmp_x_posts_v2_now.md"
else
  INTRADAY_PROMPT="/market-intraday"
  TARGET_FILE="reports/tmp_x_posts_v2_${NOW//:/}.md"
fi

setsid --wait claude -p "$INTRADAY_PROMPT" \
  --allowedTools "WebSearch Bash Read Write Glob" \
  > "$LOGDIR/market-intraday-${TIMESTAMP}.log" 2>&1
STEP1_EXIT=$?

if [ $STEP1_EXIT -ne 0 ]; then
  echo "Step 1 failed (exit=$STEP1_EXIT)" >&2
  exit 1
fi

if [[ "$NO_PUBLISH" == true ]]; then
  echo "[info] --no-publish: x-publishをスキップ" >&2
  exit 0
fi

sleep 3

# 2. X投稿実行
setsid --wait claude -p "/x-publish --auto --production --file \"${TARGET_FILE}\"" \
  --allowedTools "Read Edit Bash Glob" \
  > "$LOGDIR/x-publish-intraday-${TIMESTAMP}.log" 2>&1
STEP2_EXIT=$?

if [ $STEP2_EXIT -ne 0 ]; then
  echo "Step 2 failed (exit=$STEP2_EXIT)" >&2
  exit 1
fi
