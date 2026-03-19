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

# --- Step 4: ドラフト記事作成（demoユーザーのみ） ---

if [ "$USER" = "demo" ]; then
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
else
  echo "Skipping publish-report (user=$USER is not demo)"
fi

echo "Done. Log: $LOGFILE"
exit 0
