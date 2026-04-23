#!/bin/bash
set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M)
LOGDIR="/tmp"

# --- Step 1: バリデーション ---

# ユーザーID引数チェック
USER="${1:-}"
if [ -z "$USER" ]; then
  echo "Usage: $0 <user_id>"
  echo "  user_id: demo, test, etc."
  exit 1
fi

# Docker起動確認
if ! docker compose ps --status running 2>/dev/null | grep -q "backend"; then
  echo "Error: backend container is not running. Start with: docker compose up -d"
  exit 1
fi

# 東証取引日チェック（祝日はスキップ）
# 土日はcrontabで除外済み。ここでは日本の祝日のみチェック
if docker compose exec -T backend python3 -c "
import jpholiday
from datetime import datetime
import zoneinfo, sys
JST = zoneinfo.ZoneInfo('Asia/Tokyo')
today = datetime.now(JST).date()
sys.exit(0 if jpholiday.is_holiday(today) else 1)
" 2>/dev/null; then
  echo "Holiday detected ($(date +%Y-%m-%d)), skipping portfolio analysis."
  exit 0
fi

# --- Step 2: portfolio-analysis-v2 実行 ---

# プロンプト構築（シングルクオートEOFで展開抑制→後から変数置換）
read -r -d '' PROMPT << 'EOF'
/portfolio-analysis-v2 {USER}ユーザーのポートフォリオを分析して。

【分析指示】
データ不足などあれば原因を確認して解消しながら進めて。取得したデータや分析の内容が正しいかどうかを確認しながら実行して。コンテキスト使用サイズを抑えるように最適な実行をして。

【対象ユーザー】
- user_id: {USER}
- 認証情報: reports/{USER}/PROMPT.md またはCLAUDE.mdを参照
- 分析履歴: reports/{USER}/HISTORY.md を参照（存在する場合）
EOF

# プレースホルダーをシェル変数で置換
PROMPT="${PROMPT//\{USER\}/$USER}"

LOGFILE="$LOGDIR/portfolio-analysis-v2-${USER}-${TIMESTAMP}.log"

echo "Starting portfolio-analysis-v2 for user=$USER ..."
echo "Log: $LOGFILE"

# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

setsid --wait timeout 5400 claude -p "$PROMPT" \
  --allowedTools "WebSearch WebFetch Bash Read Write Edit Glob Grep Task TaskOutput Skill" \
  > "$LOGFILE" 2>&1
STEP2_EXIT=$?

if [ ! -s "$LOGFILE" ]; then
  echo "Warning: Log file is empty. Claude CLI may have failed to start."
  echo "Hint: Try running 'claude -p ...' manually to check for errors."
fi

if [ $STEP2_EXIT -eq 124 ]; then
  echo "Error: portfolio-analysis-v2 timed out (5400s)"
  exit 1
fi

if [ $STEP2_EXIT -ne 0 ]; then
  echo "Error: portfolio-analysis-v2 failed with exit code $STEP2_EXIT"
  exit 1
fi

sleep 3

# --- Step 3: メトリクス抽出 ---

python3 .claude/skills/portfolio-analysis/scripts/extract_metrics.py --user "$USER" 2>&1
STEP3_EXIT=$?

if [ $STEP3_EXIT -ne 0 ]; then
  echo "Warning: metrics extraction failed (exit code $STEP3_EXIT), continuing..."
fi

# --- Step 3.5: tmp_report.md 作成（要約） ---

LATEST_REPORT=$(ls -t reports/${USER}/*_${USER}.md reports/${USER}/*_${USER}_v2.md 2>/dev/null | head -1)

if [ -z "$LATEST_REPORT" ]; then
  echo "Warning: No report file found for user=$USER, skipping tmp_report generation."
else
  echo "Starting tmp_report generation: $LATEST_REPORT -> reports/$USER/tmp_report.md"

  PROMPT_TEMPLATE=".claude/skills/portfolio-analysis/prompts/tmp_report.md"
  if [ ! -f "$PROMPT_TEMPLATE" ]; then
    echo "Warning: Prompt template not found ($PROMPT_TEMPLATE), skipping."
  else
    PROMPT35=$(sed \
      -e "s|{{REPORT_PATH}}|${LATEST_REPORT}|g" \
      -e "s|{{OUTPUT_PATH}}|reports/${USER}/tmp_report.md|g" \
      "$PROMPT_TEMPLATE")

    setsid --wait timeout 300 claude -p "$PROMPT35" \
      --allowedTools "Read Write" \
      >> "$LOGFILE" 2>&1
    STEP35_EXIT=$?

    if [ $STEP35_EXIT -eq 124 ]; then
      echo "Warning: tmp_report generation timed out (300s), continuing..."
    elif [ $STEP35_EXIT -ne 0 ]; then
      echo "Warning: tmp_report generation failed (exit code $STEP35_EXIT), continuing..."
    else
      echo "tmp_report generated: reports/$USER/tmp_report.md"
    fi

    sleep 2
  fi
fi

# --- Step 4: ドラフト記事作成（demoユーザー かつ 金曜日のみ） ---
# JSTの曜日で判定（5=金曜）
DOW_JST=$(TZ=Asia/Tokyo date +%u)

if [ "$USER" = "demo" ] && [ "$DOW_JST" = "5" ]; then
  echo "Starting publish-report auto for user=$USER ..."

  read -r -d '' PROMPT4 << 'EOF'
/publish-report auto
EOF

  setsid --wait timeout 600 claude -p "$PROMPT4" \
    --allowedTools "Read Glob Grep Write Bash Skill" \
    >> "$LOGFILE" 2>&1
  STEP4_EXIT=$?

  if [ $STEP4_EXIT -eq 124 ]; then
    echo "Warning: publish-report timed out (600s), continuing..."
  elif [ $STEP4_EXIT -ne 0 ]; then
    echo "Warning: publish-report failed with exit code $STEP4_EXIT, continuing..."
  fi

  sleep 3

  # --- Step 4.5: 本番DBに記事を同期 ---

  # 今日作成されたドラフトを取得（Step 4で作成されたもの）
  TODAY=$(date +%Y%m%d)
  LATEST_DRAFT=$(ls -t reports/demo/drafts/${TODAY}_draft.md 2>/dev/null | head -1)
  if [ -z "$LATEST_DRAFT" ]; then
    # 日付一致がなければ最新を使用（フォールバック）
    LATEST_DRAFT=$(ls -t reports/demo/drafts/*_draft.md 2>/dev/null | head -1)
  fi

  if [ -n "$LATEST_DRAFT" ]; then
    echo "Starting publish_note.py --sync-production for: $LATEST_DRAFT"
    docker compose exec -T backend python scripts/publish_note.py \
      "$LATEST_DRAFT" --sync-production 2>&1
    STEP45_EXIT=$?
    echo "publish_note.py completed (exit=$STEP45_EXIT)."
  else
    echo "Warning: No draft file found, skipping DB sync."
    STEP45_EXIT=1
  fi

  # --- Step 5: X投稿文生成（記事告知） ---

  if [ "${STEP45_EXIT:-1}" -ne 0 ]; then
    echo "Warning: Step 4.5 failed (exit=$STEP45_EXIT), skipping Step 5-6 (X post)."
  else
    # slug取得: frontmatterのslugフィールド、なければファイル名stem
    DRAFT_SLUG=$(grep -m1 '^slug:' "$LATEST_DRAFT" 2>/dev/null | sed 's/^slug:[[:space:]]*//' | tr -d '"' | tr -d "'")
    if [ -z "$DRAFT_SLUG" ]; then
      DRAFT_SLUG=$(basename "$LATEST_DRAFT" .md)
    fi
    ARTICLE_URL="https://kima3.net/japan-etf-analyzer/notes/${DRAFT_SLUG}"
    TODAY_DISPLAY=$(date +%Y-%m-%d)
    NOW_HHMM=$(date +%H:%M)
    X_POSTS_FILE="reports/tmp_x_posts_v2_1800.md"

    read -r -d '' PROMPT5 << STEP5EOF
以下のドラフト記事を読み、記事公開を告知するX投稿文を1本だけ生成してください。

【ドラフトファイル】
${LATEST_DRAFT}

【記事URL】
${ARTICLE_URL}

【出力先】
${X_POSTS_FILE}

【出力フォーマット（厳守）】
\`\`\`
# X投稿 ${TODAY_DISPLAY} ${NOW_HHMM} 記事告知（1投稿構成）

---

## 投稿1
（投稿テキスト本文）
#ハッシュタグ1 #ハッシュタグ2

---
\`\`\`

【投稿ルール】
- 文字数: 270カウント前後（URLは23カウントとして計算）
- ハッシュタグ: 2-3個（#ETF #東証ETF分析 など）
- 冒頭に[テスト]を付ける（例: [テスト] 記事を公開しました）
- 記事URLを本文に含める

【キャラクター設定】
- ペルソナ: 20代後半・女性・データアナリスト
- トーン: 丁寧だけど堅くない。解説者ベース
- 語尾: 「〜です」「〜があります」「〜してみてください」
- 事実を淡々と並べた後、最後の一言にさりげなく人柄をにじませる
- 絵文字はアイコン的に使用

【手順】
1. Readで${LATEST_DRAFT}を読んでtitleとsummaryを把握
2. 投稿文を作成
3. Writeで${X_POSTS_FILE}に出力
STEP5EOF

    echo "Starting Step 5: X post draft generation..."

    setsid --wait timeout 120 claude -p "$PROMPT5" \
      --allowedTools "Read Write" \
      >> "$LOGFILE" 2>&1
    STEP5_EXIT=$?

    if [ $STEP5_EXIT -eq 124 ]; then
      echo "Warning: Step 5 (X draft) timed out (120s), skipping Step 6."
    elif [ $STEP5_EXIT -ne 0 ]; then
      echo "Warning: Step 5 (X draft) failed (exit=$STEP5_EXIT), skipping Step 6."
    else
      echo "Step 5 completed: $X_POSTS_FILE"

      sleep 3

      # --- Step 6: X実投稿 ---

      echo "Starting Step 6: X publish..."

      setsid --wait timeout 300 claude -p "/x-publish --auto --production --file \"$X_POSTS_FILE\"" \
        --allowedTools "Read Edit Bash Glob" \
        >> "$LOGFILE" 2>&1
      STEP6_EXIT=$?

      if [ $STEP6_EXIT -eq 124 ]; then
        echo "Warning: Step 6 (X publish) timed out (300s)."
      elif [ $STEP6_EXIT -ne 0 ]; then
        echo "Warning: Step 6 (X publish) failed (exit=$STEP6_EXIT)."
      else
        echo "Step 6 completed: X post published."
      fi
    fi
  fi

else
  echo "Skipping publish-report (user=$USER, dow=$DOW_JST; demo以外 または 金曜以外)"
fi

echo "Done. Log: $LOGFILE"
exit 0
