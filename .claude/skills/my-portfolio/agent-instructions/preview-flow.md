# preview-flow: F4 メールプレビュー・再送

my-portfolio スキルの **F4**。Daily Advisor メール（morning/evening/weekly）を
**原則 dry-run** でプレビューし、明示同意時のみ実送信する。
サブエージェントはこのファイルのみ Read すればよい。

## 1. kind 確定

ユーザー発話から kind を推定し、曖昧なら **AskUserQuestion** で確定する。

| 発話例 | kind |
|--------|------|
| 「朝メール」「寄り付き前」 | morning |
| 「夕方メール」「終値ベース」 | evening |
| 「週次」「ウィークリー」 | weekly |

## 2. dry-run プレビュー実行

実行コマンド（kind を置換）:

```bash
docker compose exec -T backend python3 scripts/daily_advisor_<kind>.py --dry-run
```

- 生成物: `reports/test/daily-tasks/<YYYYMMDD>_<kind>.md`
  （`AdvisorRunner._write_markdown`。dry-run でも **必ず生成**される）。
- 実メール送信はスキップされ、ログに `[DRY-RUN] Would send email: <subject>`
  が出る（`backend/scripts/_shared/advisor_runner.py` の `run()` dry_run 分岐）。
- 生成 markdown を **Read** してユーザーに提示する。

### 依存スキップ（evening のみ）

`daily_advisor_evening` は `depends_on = ["update_etf_data"]`
（`daily_advisor_evening.py`）。当日 `update_etf_data` 成功記録が無い時間帯に
プレビューすると `_check_dependencies()` が False → exit 0（markdown 未生成・
スキップ）になる。これを回避するため **`--skip-dep-check` を併用**する
（`backend/scripts/base_batch.py` で定義済みの共通フラグ。
`_check_dependencies()` が `args.skip_dep_check` で依存チェックをバイパス）:

```bash
docker compose exec -T backend python3 scripts/daily_advisor_evening.py --dry-run --skip-dep-check
```

morning / weekly は `depends_on` を持たないため `--skip-dep-check` 不要。

## 3. evening 前夜サマリ JSON 汚染ガード（必須・確定方針）

**確認結果（`backend/scripts/_shared/advisor_runner.py` Read 済）**: evening
kind では `_build_context()` 内で `rebalance_plan is not None` かつ
`self.user_id_str == "test"` のとき `_persist_evening_summary(today, plan)`
が呼ばれる（`_build_context` は `run()` の **`dry_run` 判定より前**に実行
される）。本スキルは user=`test` 固定のため、すなわち **`--dry-run` でも
前夜サマリ JSON `reports/test/daily-tasks/evening_summary_<YYYYMMDD>.json`
が上書きされる**。

これは翌朝 morning の「前夜決定事項リマインダー」セクションが当日プレビューの
内容で汚染されることを意味する（`_load_previous_evening_summary` が当日→
直近5日を遡って読むため）。

したがって evening を `--dry-run` でプレビューする場合、以下を **必須**とする:

1. **警告提示**: ユーザーに「evening のプレビューは翌朝 morning の『前夜決定
   事項リマインダー』を汚染しうるため、退避→復元を行う」と明示する。
2. **退避**（プレビュー実行の前に）:
   ```bash
   docker compose exec -T backend bash -lc '
     f="reports/test/daily-tasks/evening_summary_$(date +%Y%m%d).json"
     [ -f "$f" ] && cp -p "$f" "$f.mypf_bak" && echo "backed up: $f" || echo "no existing summary"
   '
   ```
3. **dry-run 実行**（手順2のコマンド、`--skip-dep-check` 併用）。
4. **復元**（プレビュー Read 後・必ず実行）:
   ```bash
   docker compose exec -T backend bash -lc '
     f="reports/test/daily-tasks/evening_summary_$(date +%Y%m%d).json"
     if [ -f "$f.mypf_bak" ]; then mv -f "$f.mypf_bak" "$f" && echo "restored: $f";
     else rm -f "$f" && echo "removed preview-generated summary (no prior file)"; fi
   '
   ```
   - 退避ファイルがあれば元に戻す。元々無かった（プレビューで新規生成された）
     場合は生成された JSON を削除し、汚染を残さない。
5. 復元の成否を要約に必ず含める（復元失敗時はユーザーに手動確認を促す）。

morning / weekly は `_persist_evening_summary` を呼ばないため、この退避/復元は
不要（markdown 生成のみで副作用は軽微）。

## 4. 再送（実メール送信）

- ユーザーが「再送して」「実際に送って」と **明言** し、かつ
  **AskUserQuestion** で「本当に送信しますか？」に同意した場合 **のみ**、
  `--dry-run` を外して本実行する:
  ```bash
  docker compose exec -T backend python3 scripts/daily_advisor_<kind>.py [--skip-dep-check]
  ```
- evening を本送信する場合、`_persist_evening_summary` が正規に走るので
  退避/復元は **しない**（本送信は前夜サマリの正規更新が目的のため）。
- 同意が得られない／曖昧な場合は送信せず dry-run プレビューに留める。

## 5. メインへの戻り値

要約 1〜数行のみ（例: 「evening を dry-run プレビュー。前夜サマリ JSON は
退避→復元済（元ファイルなし→生成分を削除）。メール未送信。本文ユーザー提示済」）。

## 6. フォールバック

| 状況 | 対応 |
|------|------|
| markdown 未生成（依存スキップ等） | `--skip-dep-check` 併用で再実行を1回試行 |
| 退避/復元コマンド失敗 | ユーザーに `evening_summary_*.json` の手動確認を促し報告 |
| Docker 未起動 | `docker compose up -d` を案内（メイン側で実行） |
