#!/bin/bash
# ============================================================================
# 全バッチディスパッチャ（schedulerコンテナ廃止後の集約版）
#
# ホストcronから 5分間隔で起動し、内部で時刻判定を行い該当ジョブを発火する。
# 1ジョブ失敗で他ジョブを止めないため `set -e` は使わず `-uo pipefail` のみ。
#
# オプション:
#   --at HH:MM   時刻偽装（テスト用）
#   --dow N      曜日偽装 1=月〜7=日（テスト用）
#   --dry-run    実行せず、起動するジョブを表示するのみ
#   --only NAME  指定バッチのみ実行（時刻条件を無視）
#   -h, --help   このヘルプを表示
#
# 実行モデル:
#   - 各バッチは `docker compose exec -T backend python3 scripts/<NAME>.py <ARGS>` で起動
#   - バッチ別 flock (/tmp/cron-batch-<NAME>.lock) で多重起動防止
#   - 通常モード: バックグラウンド `&` で並列起動 → スクリプト末尾で `wait`
#   - SYNCモード: foreground で同期実行（`run_chain` 経由のチェーン用、fail-stop）
#   - 各バッチログは既存の logs/<batch_name>.log を踏襲
# ============================================================================

set -uo pipefail

PROJECT_DIR="/home/t_osaka/_mydev/_test_kabu/japan-etf-analyzer-sakura"
cd "$PROJECT_DIR"

# --- 環境プロファイル ---
# CRON_BATCH_PROFILE=dev|prod (default: dev)
#   dev : 開発環境（advisor 3本 + theme_etfs + watcher を含む全ジョブ）
#   prod: 本番環境（さくら）想定。dev限定ジョブを除外
# 不正値は exit 2 で起動拒否（誤設定での意図しない発火事故を防ぐ）
declare -ra JOB_PROFILES=(
  "batch_monitor|both"
  "rotate_logs|both"
  "sync_etf_from_jpx|both"
  "update_scores_master|both"
  "sync_historical_splits|both"
  "update_etf_data|both"
  "sync_from_minkabu|both"
  "update_scores|both"
  "update_theme_etfs|dev"
  "daily_advisor_morning|dev"
  "daily_advisor_evening|dev"
  "daily_advisor_weekly|dev"
  "mechanical_rule_watcher|dev"
  "etf_rating_daily|dev"
)
PROFILE="${CRON_BATCH_PROFILE:-dev}"
if [[ "$PROFILE" != "dev" && "$PROFILE" != "prod" ]]; then
  echo "Error: CRON_BATCH_PROFILE must be 'dev' or 'prod' (got: $PROFILE)" >&2
  exit 2
fi

# --- オプション解析 ---
FAKE_TIME=""
FAKE_DOW=""
DRY_RUN=false
ONLY_NAME=""

require_arg() {
  # 必須引数欠落チェック (set -u 下でのわかりにくいエラーを回避)
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == --* ]]; then
    echo "Error: $opt requires an argument" >&2
    echo "Try: $0 --help" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --at)
      require_arg "--at" "${2:-}"; FAKE_TIME="$2"; shift 2 ;;
    --dow)
      require_arg "--dow" "${2:-}"; FAKE_DOW="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    --only)
      require_arg "--only" "${2:-}"; ONLY_NAME="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Try: $0 --help" >&2
      exit 1 ;;
  esac
done

# --- 時刻取得（FAKE_TIME / FAKE_DOW があれば優先） ---
if [[ -n "$FAKE_TIME" ]]; then
  if [[ ! "$FAKE_TIME" =~ ^[0-2][0-9]:[0-5][0-9]$ ]]; then
    echo "Error: --at must be HH:MM (got: $FAKE_TIME)" >&2
    exit 1
  fi
  NOW="$FAKE_TIME"
else
  NOW="$(TZ=Asia/Tokyo date +%H:%M)"
fi
HOUR="${NOW%:*}"
MIN="${NOW#*:}"
# 先頭ゼロを取り除いて算術比較しやすくする
HOUR_NUM=$((10#$HOUR))
MIN_NUM=$((10#$MIN))

if [[ -n "$FAKE_DOW" ]]; then
  if [[ ! "$FAKE_DOW" =~ ^[1-7]$ ]]; then
    echo "Error: --dow must be 1-7 (1=Mon..7=Sun) (got: $FAKE_DOW)" >&2
    exit 1
  fi
  DOW="$FAKE_DOW"
else
  DOW="$(TZ=Asia/Tokyo date +%u)"  # 1=月..7=日
fi

# --- 共通関数 ---

# プロファイル判定（JOB_PROFILES に基づき、現在の PROFILE で実行可かを返す）
is_enabled_for_profile() {
  local name=$1
  local entry job_name job_envs
  for entry in "${JOB_PROFILES[@]}"; do
    job_name=${entry%|*}
    job_envs=${entry#*|}
    if [[ "$job_name" == "$name" ]]; then
      [[ "$job_envs" == "both" ]] && return 0
      [[ "$job_envs" == "$PROFILE" ]] && return 0
      return 1
    fi
  done
  return 1   # 未定義は安全側に倒して拒否
}

# backend コンテナ起動チェック
backend_running() {
  docker compose ps --status running 2>/dev/null | grep -q "backend"
}

# 平日判定 (月〜金)
is_weekday() {
  [[ "$DOW" -ge 1 && "$DOW" -le 5 ]]
}

# 日本の祝日判定（dry-run時はキャッシュ的に false 扱いで良いが、実弾時は判定）
# 注: docker exec を発行するため、頻発する処理だが計画通り過剰最適化はしない
is_holiday() {
  if [[ "$DRY_RUN" == true ]]; then
    return 1
  fi
  docker compose exec -T backend python3 -c "
import jpholiday
from datetime import datetime
import zoneinfo, sys
JST = zoneinfo.ZoneInfo('Asia/Tokyo')
today = datetime.now(JST).date()
sys.exit(0 if jpholiday.is_holiday(today) else 1)
" 2>/dev/null
}

# 旧 backend/crontab のログ名マッピング（既存 logs/*.log を踏襲）
# 旧cronで使われていたログ名をそのまま使い、rotate_logs.pyの管理対象を変えない
log_name_for() {
  case "$1" in
    sync_etf_from_jpx)       echo "master_sync" ;;
    update_scores_master)    echo "score_update" ;;
    update_etf_data)         echo "etf_update" ;;
    sync_from_minkabu)       echo "minkabu_sync" ;;
    update_scores)           echo "score_update" ;;
    sync_historical_splits)  echo "split_sync" ;;
    update_theme_etfs)       echo "theme_etfs" ;;
    rotate_logs)             echo "rotate" ;;
    batch_monitor)           echo "batch_monitor" ;;
    daily_advisor_morning)   echo "advisor_morning" ;;
    daily_advisor_evening)   echo "advisor_evening" ;;
    daily_advisor_weekly)    echo "advisor_weekly" ;;
    mechanical_rule_watcher) echo "advisor_watcher" ;;
    etf_rating_daily)        echo "etf_rating" ;;
    *)                       echo "$1" ;;
  esac
}

# 実行スクリプト名解決（update_scores_master は実体 update_scores.py）
script_name_for() {
  case "$1" in
    update_scores_master) echo "update_scores" ;;
    *)                    echo "$1" ;;
  esac
}

# バッチ実行: run_batch <NAME> <ARGS...>
# - 既存schedulerコンテナと同じ実行方式 (cwd=/app, 同じpython環境)
# - バッチ別 flock で多重起動防止
# - 通常モード: バックグラウンド起動 (`&`) で並列実行
# - SYNC=true:  foreground 同期実行（チェーン用、exit code を return、flock失敗で exit 2）
run_batch() {
  local name="$1"; shift
  local args=("$@")

  # プロファイル判定（最先頭）
  if ! is_enabled_for_profile "$name"; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "[dry-run] SKIP-profile=${PROFILE} ${name} ${args[*]}"
    fi
    return 0
  fi

  local logname
  logname="$(log_name_for "$name")"
  local script
  script="$(script_name_for "$name")"
  local logfile="$PROJECT_DIR/logs/${logname}.log"
  local lockfile="/tmp/cron-batch-${name}.lock"

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] RUN ${name} ${args[*]} (log: $logfile)"
    return 0
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] dispatch: ${name} ${args[*]}"

  # ログ書き込みはコンテナ内シェル経由で行う（既存ログがコンテナroot所有のため、
  # ホスト側 `>>` でroot所有ファイルに追記できないことを回避）。
  # コンテナ内 cron 時代と同じ書き込み挙動 = root権限・/app/logs/ への append。
  local container_logfile="/app/logs/${logname}.log"

  # 引数を quote-safe にしてコンテナ内シェルに渡す
  local args_str=""
  for a in "${args[@]}"; do
    args_str+=" $(printf '%q' "$a")"
  done

  # 同期モード（チェーン用）: foreground実行・exit codeをreturn
  if [[ "${SYNC:-false}" == true ]]; then
    (
      flock -n 9 || {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${name}] skip (locked) — chain stops"
        exit 2
      }
      docker compose exec -T backend bash -c "
        {
          echo \"==== \$(date '+%Y-%m-%d %H:%M:%S') ${name} ${args[*]} ====\"
          python3 scripts/${script}.py${args_str}
          echo \"==== \$(date '+%Y-%m-%d %H:%M:%S') ${name} done (exit=\$?) ====\"
        } >> ${container_logfile} 2>&1
      "
    ) 9>"$lockfile"
    return $?
  fi

  # 通常モード（並列実行）: flock -n で多重起動防止 → バックグラウンド起動
  (
    flock -n 9 || { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${name}] skip (locked)"; exit 0; }
    docker compose exec -T backend bash -c "
      {
        echo \"==== \$(date '+%Y-%m-%d %H:%M:%S') ${name} ${args[*]} ====\"
        python3 scripts/${script}.py${args_str}
        echo \"==== \$(date '+%Y-%m-%d %H:%M:%S') ${name} done (exit=\$?) ====\"
      } >> ${container_logfile} 2>&1
    "
  ) 9>"$lockfile" &
}

# 依存性チェーン（fail-stop, 同期実行）
# 例: run_chain "sync_etf_from_jpx" "update_scores_master --skip-dep-check" "sync_historical_splits --all --rate-limit 3.0"
run_chain() {
  local spec
  for spec in "$@"; do
    local name="${spec%% *}"
    local args=""
    [[ "$spec" == *" "* ]] && args="${spec#* }"
    # word splitting で args を可変長引数化（args 内に空白を含む単一引数は今回未使用）
    if ! SYNC=true run_batch "$name" $args; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] chain broken at ${name}, stopping"
      return 1
    fi
  done
}

# 「時刻が HH:MM と一致するか」判定（5分グリッドの直接マッチ用）
at_time() {
  local target="$1"
  [[ "$NOW" == "$target" ]]
}

# 「分が SPEC に含まれ、時刻が HOUR_FROM〜HOUR_TO 内」判定
# 例: in_minute_window "0,10,20,30,40,50" 16 20  → */10 16-20
in_minute_window() {
  local minute_spec="$1"
  local hour_from="$2"
  local hour_to="$3"
  if (( HOUR_NUM < hour_from || HOUR_NUM > hour_to )); then
    return 1
  fi
  IFS=',' read -ra mins <<< "$minute_spec"
  for m in "${mins[@]}"; do
    if (( MIN_NUM == m )); then return 0; fi
  done
  return 1
}

# ============================================================================
# 当日キャッチアップ機構（pull型 sweep）
# ----------------------------------------------------------------------------
# 設計詳細は docs/10_バッチ処理設計.md「7. 障害時対応 / 当日キャッチアップ機構」参照
#
# 5分ごとの sweep で「予定時刻を過ぎたが当日まだ成功記録のないバッチ」を発火する。
# 連鎖は次の */5 サイクルに委ねる（fixed-point ループは導入しない／YAGNI）。
#
# エントリ書式: "name|sched|until|dow|profile"
#   sched   発火開始時刻（HH:MM、これ以降が catch-up 対象）
#   until   発火打ち切り時刻（HH:MM、これを超えたら諦め）
#   dow     weekday | daily | mon | fri | sun（曜日条件）
#   profile both | dev | prod（実行プロファイル）
#
# 対象外:
#   - batch_monitor / update_scores / mechanical_rule_watcher
#       （いずれも高頻度（*/5・*/10）でリカバリ自体が短期サイクル内に含まれる）
#   - 月曜マスタチェーン (sync_etf_from_jpx / update_scores_master / sync_historical_splits)
#       run_chain による fail-stop 同期実行が前提のため、個別 catch-up は設計と整合しない。
#       update_scores_master は実体 update_scores.py の check_window=(16:30,22:00) により
#       午前帯の発火がほぼ skip され、sync_historical_splits は depends_on を持たないため
#       並列発火時の順序保証ができない。月曜障害時は手動で run_chain 再実行する運用。
# ============================================================================

declare -ra CATCHUP_JOBS=(
  "update_etf_data|16:00|22:00|weekday|both"
  "sync_from_minkabu|16:00|22:00|weekday|both"
  "daily_advisor_morning|07:00|09:00|weekday|dev"
  "daily_advisor_evening|17:30|22:00|weekday|dev"
  "daily_advisor_weekly|18:00|22:00|fri|dev"
  "update_theme_etfs|03:00|23:59|sun|dev"
  "rotate_logs|05:00|23:59|daily|both"
  "etf_rating_daily|18:15|22:00|weekday|dev"
)

# HH:MM を分単位の整数に変換
hhmm_to_minutes() {
  local hhmm="$1"
  local h=$((10#${hhmm%:*}))
  local m=$((10#${hhmm#*:}))
  echo $(( h * 60 + m ))
}

# 曜日条件判定
#   weekday: 月〜金
#   daily  : 毎日
#   mon    : 月曜のみ
#   fri    : 金曜のみ
#   sun    : 日曜のみ
catchup_dow_ok() {
  local spec="$1"
  case "$spec" in
    weekday) [[ "$DOW" -ge 1 && "$DOW" -le 5 ]] ;;
    daily)   return 0 ;;
    mon)     [[ "$DOW" == "1" ]] ;;
    fri)     [[ "$DOW" == "5" ]] ;;
    sun)     [[ "$DOW" == "7" ]] ;;
    *)       return 1 ;;
  esac
}

# 祝日スキップ可否判定（既存 dispatch 表の挙動と整合させる）
#   - weekday 対象: 祝日スキップ
#   - mon (月曜マスタチェーン): 祝日でも実行（既存と同じ）
#   - fri (weekly): 祝日でも実行（既存と同じ）
#   - sun / daily : 祝日無関係
catchup_holiday_ok() {
  local spec="$1"
  case "$spec" in
    weekday) is_holiday && return 1 || return 0 ;;
    *)       return 0 ;;
  esac
}

# プロファイル一致判定（both は常にOK）
catchup_profile_ok() {
  local entry="$1"
  [[ "$entry" == "both" || "$entry" == "$PROFILE" ]]
}

# has_succeeded_today.py の exit code を catch-up 判定へ変換する純粋関数。
# docker 実体に依存しないため回帰テストから直接呼べる（scripts/tests/test_catchup_decision.sh）。
#   rc=0 成功済み → 1 (対象外) / rc=1 未成功 → 0 (対象) / rc>=2 エラー → 1 (安全側で対象外)
# 戻り: 0=catch-up対象, 1=対象外
catchup_decision_from_rc() {
  local name="$1" rc="$2"
  if (( rc == 1 )); then
    return 0
  elif (( rc >= 2 )); then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [catchup] has_succeeded_today.py error for ${name} (rc=${rc}), skip"
    return 1
  fi
  return 1
}

# 「catch-up すべきか」判定
# 引数: name sched until dow profile
# 戻り: 0=catch-up対象, 1=対象外
should_catchup() {
  local name="$1" sched="$2" until_="$3" dow_spec="$4" profile_spec="$5"

  # プロファイル一致
  catchup_profile_ok "$profile_spec" || return 1

  # 曜日OK
  catchup_dow_ok "$dow_spec" || return 1

  # 祝日OK
  catchup_holiday_ok "$dow_spec" || return 1

  # 時刻範囲: sched < now <= until
  # 注: sched ピッタリは通常の dispatch が拾うので catch-up からは外す（重複防止）
  local now_min sched_min until_min
  now_min=$(hhmm_to_minutes "$NOW")
  sched_min=$(hhmm_to_minutes "$sched")
  until_min=$(hhmm_to_minutes "$until_")
  if (( now_min <= sched_min || now_min > until_min )); then
    return 1
  fi

  # 今日まだ成功していないか
  if [[ "$DRY_RUN" == true ]]; then
    # dry-run 時は backend に問い合わせない前提（テスト容易性のため未成功扱い）
    return 0
  fi
  # `if ! cmd; then rc=$?` は否定後の値(=0)を拾い本来の exit を握り潰すため、
  # コマンドを直接走らせて $? を捕捉する（rc 0/1/2 を区別する必要がある）。
  docker compose exec -T backend python3 scripts/has_succeeded_today.py "$name" >/dev/null 2>&1
  local rc=$?
  catchup_decision_from_rc "$name" "$rc"
}

# catch-up sweep: 全エントリを評価し、対象なら既存 run_batch 経由で発火
catch_up_sweep() {
  local entry name sched until_ dow_spec profile_spec
  for entry in "${CATCHUP_JOBS[@]}"; do
    IFS='|' read -r name sched until_ dow_spec profile_spec <<< "$entry"
    if should_catchup "$name" "$sched" "$until_" "$dow_spec" "$profile_spec"; then
      if [[ "$DRY_RUN" == true ]]; then
        echo "[CATCHUP] ${name} due (sched=${sched}, until=${until_}, dow=${dow_spec}, profile=${profile_spec})"
      else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [catchup] dispatching ${name}"
      fi
      # 既存 dispatch と同じ引数で発火（--only と同じマッピング）
      case "$name" in
        update_etf_data)         run_batch update_etf_data --smart --rate-limit 3.0 ;;
        sync_from_minkabu)       run_batch sync_from_minkabu --rate-limit 1.5 ;;
        etf_rating_daily)
          if [[ "$DRY_RUN" == true ]]; then
            echo "[dry-run] RUN etf_rating_daily (via bash scripts/cron-etf-rating-daily.sh)"
          else
            bash scripts/cron-etf-rating-daily.sh &
          fi ;;
        *)                       run_batch "$name" ;;
      esac
    fi
  done
}

# source された場合（回帰テスト）はここまでの関数定義のみ読み込み、dispatch を実行しない。
# ${BASH_SOURCE[0]} != ${0} なら source 経由。
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0
fi

# --- 早期exit: backend が動いていなければ何もしない ---
if [[ "$DRY_RUN" != true ]]; then
  if ! backend_running; then
    # ログにも出力したいので logs/cron-batch.log の上流（cronのリダイレクト先）に出す
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] backend not running, exit"
    exit 0
  fi
fi

# --- --only モード ---
if [[ -n "$ONLY_NAME" ]]; then
  case "$ONLY_NAME" in
    batch_monitor)            run_batch batch_monitor ;;
    rotate_logs)              run_batch rotate_logs ;;
    sync_etf_from_jpx)        run_batch sync_etf_from_jpx ;;
    update_scores_master)     run_batch update_scores_master --skip-dep-check ;;
    update_etf_data)          run_batch update_etf_data --smart --rate-limit 3.0 ;;
    sync_from_minkabu)        run_batch sync_from_minkabu --rate-limit 1.5 ;;
    update_scores)            run_batch update_scores ;;
    sync_historical_splits)   run_batch sync_historical_splits --all --rate-limit 3.0 ;;
    update_theme_etfs)        run_batch update_theme_etfs ;;
    daily_advisor_morning)    run_batch daily_advisor_morning ;;
    daily_advisor_evening)    run_batch daily_advisor_evening ;;
    daily_advisor_weekly)     run_batch daily_advisor_weekly ;;
    mechanical_rule_watcher)  run_batch mechanical_rule_watcher ;;
    etf_rating_daily)
      if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] RUN etf_rating_daily (via bash scripts/cron-etf-rating-daily.sh)"
      else
        bash scripts/cron-etf-rating-daily.sh
      fi ;;
    *)
      echo "Unknown --only target: $ONLY_NAME" >&2
      exit 1 ;;
  esac
  wait
  exit 0
fi

# ============================================================================
# ディスパッチ表（旧 backend/crontab を完全踏襲）
# ============================================================================

# 1) batch_monitor: */5 * * * *  常時（祝日含む）
if (( MIN_NUM % 5 == 0 )); then
  run_batch batch_monitor
fi

# 2) rotate_logs: 0 5 * * *  毎日（祝日含む）
if at_time "05:00"; then
  run_batch rotate_logs
fi

# 3) 月曜 06:00 マスタ更新チェーン（祝日でも実行）
#    sync_etf_from_jpx → update_scores_master --skip-dep-check → sync_historical_splits --all --rate-limit 3.0
#    fail-stop: 途中で失敗したら後続をスキップ（本番crontabの `&&` 連結と同等）
if at_time "06:00" && [[ "$DOW" == "1" ]]; then
  run_chain \
    "sync_etf_from_jpx" \
    "update_scores_master --skip-dep-check" \
    "sync_historical_splits --all --rate-limit 3.0"
fi

# 4) update_etf_data: 0 16 * * 1-5  平日（祝日スキップ）
if at_time "16:00" && is_weekday && ! is_holiday; then
  run_batch update_etf_data --smart --rate-limit 3.0
fi

# 5) sync_from_minkabu: 0 16 * * 1-5  平日（祝日スキップ）
if at_time "16:00" && is_weekday && ! is_holiday; then
  run_batch sync_from_minkabu --rate-limit 1.5
fi

# 6) update_scores: */10 16-20 * * 1-5  平日（祝日スキップ）
if in_minute_window "0,10,20,30,40,50" 16 20 && is_weekday && ! is_holiday; then
  run_batch update_scores
fi

# 7) update_theme_etfs: 0 3 * * 0  日曜
if at_time "03:00" && [[ "$DOW" == "7" ]]; then
  run_batch update_theme_etfs
fi

# 8) daily_advisor_morning: 0 7 * * 1-5  平日（祝日スキップ）  [dev限定]
#    リバランス計画は morning 内に統合済み（旧 daily_advisor_rebalance 07:15 は廃止）。
if at_time "07:00" && is_weekday && ! is_holiday; then
  run_batch daily_advisor_morning
fi

# 9) daily_advisor_evening: 30 17 * * 1-5  平日（祝日スキップ）  [dev限定]
if at_time "17:30" && is_weekday && ! is_holiday; then
  run_batch daily_advisor_evening
fi

# 9.5) etf_rating_daily: 月〜木 18:00 / 金 18:15（祝日スキップ）  [dev限定]
#      金曜は daily_advisor_weekly (18:00) と並列を避けるため 18:15 起動
#      Claude CLI で /etf-rating all --send-mail を起動（bash 直接呼び出し）
if is_weekday && ! is_holiday && is_enabled_for_profile etf_rating_daily; then
  if { [[ "$DOW" != "5" ]] && at_time "18:00"; } || { [[ "$DOW" == "5" ]] && at_time "18:15"; }; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "[dry-run] RUN etf_rating_daily (via bash scripts/cron-etf-rating-daily.sh)"
    else
      bash scripts/cron-etf-rating-daily.sh &
    fi
  fi
fi

# 10) daily_advisor_weekly: 0 18 * * 5  金曜（祝日でも実行 ※週末入りの整理目的）  [dev限定]
if at_time "18:00" && [[ "$DOW" == "5" ]]; then
  run_batch daily_advisor_weekly
fi

# 11) mechanical_rule_watcher: */5 9-15 * * 1-5  平日（祝日スキップ）  [dev限定]
if (( MIN_NUM % 5 == 0 )) && (( HOUR_NUM >= 9 && HOUR_NUM <= 15 )) && is_weekday && ! is_holiday; then
  run_batch mechanical_rule_watcher
fi

# 12) catch-up sweep: 予定時刻を逃したバッチを当日中に追走
#     （高頻度バッチ（*/5・*/10）は対象外）
catch_up_sweep

# --- 全バックグラウンドジョブの完了を待つ ---
wait
exit 0
