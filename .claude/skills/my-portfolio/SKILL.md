---
name: my-portfolio
description: test ユーザーのポートフォリオ計画を対話確認・管理（損益/配分/銘柄変更/メールプレビュー）
user-invocable: true
aliases: ["/my-portfolio", "/mypf"]
allowed-tools: Read, Grep, Glob, Bash, Task, AskUserQuestion, Edit
---

# my-portfolio

test ユーザーのポートフォリオ計画（A群/B群の目標配分・機械ルール）の状態を
自然言語で確認・管理するプロジェクトスキル。既存の `AdvisorRunner` /
`PortfolioService` / 戦略改訂手順を薄くラップする。新規ロジックは最小限。

## 環境前提

| 項目 | 値 |
|------|-----|
| 実行環境 | 開発（Docker） |
| 対象ユーザー | `test`（`user_id` 文字列） |
| 戦略SSOT | `docs/12_personal_strategy.md`（改訂手順: `docs/12a_戦略書改訂手順.md`） |
| メール仕様 | `docs/06b_メール通知仕様.md` |
| reports 出力先 | `reports/test/daily-tasks/`（`<YYYYMMDD>_<kind>.md` / `evening_summary_*.json`） |
| read-only ヘルパ | `backend/scripts/portfolio_status.py`（`docker compose exec -T backend python3 scripts/portfolio_status.py`） |

- `.claude/` は backend コンテナに未マウント。スクリプトは必ず
  `/app/scripts`（= `backend/scripts/`）経由で実行する。
- 損益・価格・配分の計算前に必ず CLAUDE.md「株式分割の管理」ルールを適用
  （対象銘柄の `stock_splits` 確認・PortfolioService 経由＝分割調整済み・
  DB直クエリ/データソース混在禁止）。

## 意図ルーター（4フロー）

ユーザー発話から意図を分類し、対応フローに委譲する。

| 意図キーワード例 | フロー | 種別 | 指示ファイル |
|-----------------|--------|------|------------|
| 「いくら儲かってる」「損益」「総資産」「保有銘柄」「含み損益」 | F1 損益・資産確認 | read-only | `agent-instructions/read-flows.md` |
| 「配分」「乖離」「A群/B群」「リバランス」「目標比率」「次の基準日」 | F2 配分・乖離確認 | read-only | `agent-instructions/read-flows.md` |
| 「銘柄を入れ替えたい」「○○を追加/外したい」「戦略を変えたい」 | F3 銘柄変更（アシスト型） | 書き込み | `agent-instructions/strategy-revision.md` |
| 「メールを見せて」「夕方/朝/週次メール」「プレビュー」「再送して」 | F4 メールプレビュー・再送 | 原則 read-only | `agent-instructions/preview-flow.md` |

- 意図が曖昧・複合の場合は **AskUserQuestion** で1つに確定してから委譲する。
- F1/F2 はどちらも read-flows.md（共通ヘルパ `portfolio_status.py`）を使う。

## 読み書きガード

| フロー | DB/ファイル副作用 | ガード |
|--------|-----------------|--------|
| F1 / F2 | なし（read-only） | `portfolio_status.py` は INSERT/UPDATE/DELETE なし |
| F4 | 原則 dry-run（markdown 生成 + evening は JSON 退避/復元） | 実メール送信は AskUserQuestion 明示同意時のみ |
| F3 | docs/12・docs/06b・fixture を Edit | 差分は AskUserQuestion 承認後のみ。pytest/commit は人手 |

## メインエージェント委譲ルール

- `agent-instructions/` 配下のファイルは **メインエージェントが読み込まない**。
  メインはサブエージェント（Task）のプロンプトに **指示ファイルパス＋パラメータ**
  だけを渡す。サブエージェントが自分の指示ファイルを Read して実行する。
- 各フローでサブエージェントが読むファイルは最小化する（F1/F2 →
  read-flows.md のみ / F3 → strategy-revision.md のみ / F4 → preview-flow.md のみ）。
- サブエージェントはメインに **要約（1〜数行）のみ** 返す。整形済み出力本文は
  必要に応じてメインがユーザーへ提示する。
- F3 の docs/fixture 編集は、コンテナ内 read-only マウントを避けるため
  **ホスト側 Edit ツール**で行う（メイン or サブエージェント）。

## フロー概要

- **F1 損益・資産確認**: `portfolio_status.py` 実行 → split 検証 → 総資産・現金・
  評価損益額/率・銘柄別損益・保有日数を整形提示（期間リターン/α は weekly に委譲）。
- **F2 配分・乖離確認**: 同ヘルパで A群/B群 実績vs目標・drift_pp・
  next_rebalance_date を整形提示。
- **F3 銘柄変更（アシスト型）**: 登録確認 → 差分案承認 → docs/12・docs/06b・
  fixture4種を Edit → 確認サマリ提示で **停止**（pytest/commit は人手）。
- **F4 メールプレビュー・再送**: kind 選択 → `--dry-run` プレビュー →
  明示同意時のみ再送。evening は前夜サマリ JSON の汚染ガード必須。

詳細は各 `agent-instructions/*.md` を参照（パスは上表のとおり）。

## 関連

| 参照 | 用途 |
|------|------|
| `docs/12_personal_strategy.md` | 戦略SSOT |
| `docs/12a_戦略書改訂手順.md` | F3 の改訂手順原典（事前チェック2＋実装6＋動作確認2 の10ステップ） |
| `docs/06b_メール通知仕様.md` | F4 メール仕様・F3 改訂履歴追記先 |
| `backend/scripts/_shared/advisor_runner.py` | F4 メール生成ランナー |
| `backend/scripts/portfolio_status.py` | F1/F2 read-only ヘルパ |
