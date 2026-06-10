#!/bin/bash
# ============================================================================
# 回帰テスト: catch-up 判定が has_succeeded_today.py の exit code を
# 正しく解釈するか検証する（A-1 のバグ再発防止）。
#
# 過去バグ: `if ! cmd; then rc=$?` で $? が否定後の値(=0)になり、
# 未成功(rc=1)でも catch-up 対象にならず全件 skip していた。
#
# docker 実体に依存しないよう、rc→判定ロジックを切り出した
# catchup_decision_from_rc を cron-batch.sh から source して直接呼ぶ。
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$SCRIPT_DIR/../cron-batch.sh"

# source で関数定義のみ読み込む（dispatch は BASH_SOURCE ガードで抑止される）。
# shellcheck source=../cron-batch.sh
source "$TARGET"

FAIL=0

# 期待: rc=0 成功済み→1(skip) / rc=1 未成功→0(due) / rc=2,3 エラー→1(skip)
assert_decision() {
  local desc="$1" rc="$2" expected="$3"
  catchup_decision_from_rc "dummy_batch" "$rc" >/dev/null 2>&1
  local actual=$?
  if (( actual == expected )); then
    echo "PASS: ${desc} (rc=${rc} → ${actual})"
  else
    echo "FAIL: ${desc} (rc=${rc} → got ${actual}, want ${expected})"
    FAIL=1
  fi
}

assert_decision "rc=0 成功済みは skip" 0 1
assert_decision "rc=1 未成功は catch-up 対象(due)" 1 0
assert_decision "rc=2 エラーは安全側 skip" 2 1
assert_decision "rc=3 想定外も skip" 3 1

# 成功判定に使う batch_logs.batch_name 解決。
# 過去バグ: catch-up が etf_rating_daily を has_succeeded_today へそのまま渡すが、
# 実体は batch_name='etf_rating_send_mail' で記録されるため当日成功を検知できず、
# until まで5分おきに再発火しメールを重複送信していた。
assert_success_name() {
  local desc="$1" job="$2" expected="$3"
  local actual
  actual=$(success_name_for "$job")
  if [[ "$actual" == "$expected" ]]; then
    echo "PASS: ${desc} (${job} → ${actual})"
  else
    echo "FAIL: ${desc} (${job} → got '${actual}', want '${expected}')"
    FAIL=1
  fi
}

assert_success_name "etf_rating_daily は実記録名へ変換" etf_rating_daily etf_rating_send_mail
assert_success_name "通常ジョブはジョブ名のまま" update_etf_data update_etf_data

if (( FAIL == 0 )); then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "SOME TESTS FAILED"
  exit 1
fi
