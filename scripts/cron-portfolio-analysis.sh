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
  echo "Usage: $0 <user_id> [mode]"
  echo "  user_id: demo, test, etc."
  echo "  mode:    debate (default), normal, speed"
  exit 1
fi

# モード引数チェック
MODE="${2:-debate}"
if [ "$MODE" != "debate" ] && [ "$MODE" != "normal" ] && [ "$MODE" != "speed" ]; then
  echo "Error: Invalid mode '$MODE'. Must be one of: debate, normal, speed"
  exit 1
fi

# Docker起動確認
if ! docker compose ps --status running 2>/dev/null | grep -q "backend"; then
  echo "Error: backend container is not running. Start with: docker compose up -d"
  exit 1
fi

# --- Step 2: portfolio-analysis 実行 ---

# モード別の分析指示
case "$MODE" in
  debate)
    MODE_INSTRUCTION="エージェントチームによる議論型で徹底的に議論して最適な分析を達成して。データ不足などあれば原因があるはずなので確認して解消しながら進めて。取得したデータや分析の内容が正しいかどうかを確認しながら実行して"
    ;;
  normal)
    MODE_INSTRUCTION="バランス重視で分析して。データの正確性を確認しながら進めて"
    ;;
  speed)
    MODE_INSTRUCTION="速度重視で分析して。主要な指標を中心に効率的に進めて"
    ;;
esac

# プロンプト構築（シングルクオートEOFで展開抑制→後から変数置換）
read -r -d '' PROMPT << 'EOF'
/portfolio-analysis {USER}ユーザーのポートフォリオを分析して。

【モード指定】
分析モードは「{MODE}」で実行。AskUserQuestionによるモード確認はスキップして直接開始。

【分析指示】
{MODE_INSTRUCTION}

【対象ユーザー】
- user_id: {USER}
- 認証情報: reports/{USER}/PROMPT.md またはCLAUDE.mdを参照
- 分析履歴: reports/{USER}/HISTORY.md を参照（存在する場合）
EOF

# プレースホルダーをシェル変数で置換
PROMPT="${PROMPT//\{USER\}/$USER}"
PROMPT="${PROMPT//\{MODE\}/$MODE}"
PROMPT="${PROMPT//\{MODE_INSTRUCTION\}/$MODE_INSTRUCTION}"

LOGFILE="$LOGDIR/portfolio-analysis-${USER}-${TIMESTAMP}.log"

echo "Starting portfolio-analysis for user=$USER mode=$MODE ..."
echo "Log: $LOGFILE"

# Claude CLIセッション内からの実行対策（入れ子セッション防止）
unset CLAUDECODE

timeout 3600 claude -p "$PROMPT" \
  --allowedTools "WebSearch WebFetch Bash Read Write Edit Glob Grep Task TaskOutput Skill" \
  > "$LOGFILE" 2>&1
STEP2_EXIT=$?

if [ ! -s "$LOGFILE" ]; then
  echo "Warning: Log file is empty. Claude CLI may have failed to start."
  echo "Hint: Try running 'claude -p ...' manually to check for errors."
fi

if [ $STEP2_EXIT -eq 124 ]; then
  echo "Error: portfolio-analysis timed out (3600s)"
  exit 1
fi

if [ $STEP2_EXIT -ne 0 ]; then
  echo "Error: portfolio-analysis failed with exit code $STEP2_EXIT"
  exit 1
fi

sleep 3

# --- Step 3: メトリクス抽出 ---

python3 .claude/skills/portfolio-analysis/scripts/extract_metrics.py --user "$USER" 2>&1
STEP3_EXIT=$?

if [ $STEP3_EXIT -ne 0 ]; then
  echo "Warning: metrics extraction failed (exit code $STEP3_EXIT), continuing..."
fi

echo "Done. Log: $LOGFILE"
exit 0
