---
name: etf-rating
description: 個別ETF銘柄の中期マッチ度を採点（上昇10×下落10、Top5重み×2、3シナリオ）。target_holdings + watchlist 全銘柄を毎平日（月-木 18:00 / 金 18:15）に一括評価しメール配信
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Task, TaskOutput, WebSearch, WebFetch, AskUserQuestion, Write
aliases: ["/etf-rating", "/rating"]
---

# etf-rating

個別ETF銘柄について、銘柄ごとにカスタムされた「上昇10条件 × 下落10条件」を
現在の市場情勢にマッチングさせて 0〜100 点で採点し、Top5ドライバーに重み×2 を
かけてネット中期スコア・先取り/後追い区分・3シナリオまで一気通貫で出力する
プロジェクトスキル。手作業で実施した `reports/research/1629_evaluation_20260522.md`
の評価フレームを汎用化・自動化したもの。

## スコープと棲み分け

| スキル | 焦点 | 主要出力 |
|--------|------|----------|
| `/etf-rating` | **個別銘柄 × 現在情勢のマッチ度** | 銘柄別レポート + 1通メール |
| `/my-portfolio` | test ユーザーの保有・配分・乖離 | 損益/配分プレビュー |
| `/pf-v2` | ポートフォリオ全体のリスク・分散・品質 | 総合分析レポート |
| `/market-outlook-v2` | 当日の東証見通し・振り返り | 朝/夕レポート |

このスキルは「個別銘柄が今この瞬間に追い風か逆風か」だけを判定する。
ポートフォリオ全体の最適化や東証マクロ見通しは別スキルの責務。

## 操作モード

| コマンド | 動作 |
|----------|------|
| `/etf-rating <code>` | 単一銘柄を評価。レポートのみ生成（メール送信なし）。手動検証用 |
| `/etf-rating all` | target_holdings 全銘柄 + watchlist を順次評価。メール送信なし |
| `/etf-rating all --send-mail` | 全銘柄評価 + メール送信。cron 自動実行はこの形 |
| `/etf-rating tune <code>` | 観点（criteria YAML）の見直し対話。過去履歴・直近採点を踏まえ提案 |
| `/etf-rating <code> --send-mail` | 単一銘柄をメール送信付きで実行（緊急再配信用） |

### 自動実行モード判定（cron 起動時の保証）

- 引数に `--send-mail` が含まれる **または** 環境変数 `ETF_RATING_NONINTERACTIVE=1`
  が設定されている場合、**AskUserQuestion をスキップする**。
- 判断に迷う分岐（対象ユーザー・watchlist 取込範囲・スコア欠損時の挙動など）は
  **デフォルト選択肢を採用**し、選択内容を `{WORK_DIR}/decisions.log` に追記。
- 対話モード（インタラクティブ起動）では従来どおり AskUserQuestion で確認。

## コンテキスト管理

### 作業ディレクトリ

```bash
DATE_YMD=$(date +%Y%m%d)
WORK_DIR=".tmp/etf-rating_${DATE_YMD}"
mkdir -p "${WORK_DIR}"
```

同日中に複数回実行された場合は同一ディレクトリを再利用（中間ファイルは上書き）。
日次冪等性のためサフィックスは付けない。

### データ受け渡しルール

| ルール | 説明 |
|--------|------|
| ファイルベース通信 | 全中間データは `WORK_DIR` 内のファイルに保存 |
| 要約のみ返却 | サブエージェントはメインに1-2行の完了報告のみ返す |
| メインは中間ファイルをReadしない | パスのみ管理 |
| agent-instructions はサブ側で Read | メインは指示ファイルパスをプロンプトで渡すのみ |

## 共通設定

| 項目 | 値 |
|------|-----|
| target_holdings 取得元 | `docs/12_personal_strategy.md` の frontmatter YAML |
| watchlist 取得元 | `.claude/skills/etf-rating/criteria/watchlist/*.yaml`（任意） |
| 観点 YAML | `.claude/skills/etf-rating/criteria/{code}.yaml` |
| 共通閾値・重み | `.claude/skills/etf-rating/calc_params.json` |
| 採点履歴 | `data/etf-rating/history/{code}.jsonl`（1日1行追記） |
| レポート出力 | `reports/etf-rating/{code}/{YYYYMMDD}_{code}_rating.md` |
| 集計サマリ | `reports/etf-rating/_daily_summary/{YYYYMMDD}.md` |
| メールペイロード | `{WORK_DIR}/email_payload.json` |

## 実行フロー

`{skill_dir}` = `.claude/skills/etf-rating`

### Step 0: 初期化

1. WORK_DIR を作成
2. モード判定（単一/全/tune、`--send-mail` 有無、`ETF_RATING_NONINTERACTIVE`）
3. target_holdings + watchlist を読み込み、対象コードリストを確定
4. インタラクティブモードのみ AskUserQuestion で対象確認

### Step 1: Phase 0 市場スナップショット（共通・1回のみ）

サブエージェント（Task, general-purpose）を1つ起動。WebSearch で当日の市場環境
を取得し、全銘柄の Phase 1 評価で共通参照する「マクロ環境スナップショット」を作成。

- 指示: `{skill_dir}/agent-instructions/phase0-market-snapshot.md`
- 入力: `WORK_DIR`, `calc_params.json`
- 出力: `{WORK_DIR}/00_market_snapshot.md`
- 戻り値: 「Phase 0 完了（検索回数: N回）」の1行

**重要**: Phase 0 で取得した情勢は Phase 1 各銘柄評価で**参照のみ**とし、Phase 1
内で同一テーマを再検索しない（総検索回数を 30 回以内に抑える）。

### Step 2: Phase 1 単一銘柄評価（最大4並列）

対象コードを最大4並列で Task 起動（`run_in_background: true`）。

- 指示: `{skill_dir}/agent-instructions/phase1-single-rating.md`
- 入力: `WORK_DIR`, `CODE`, `CRITERIA_PATH` = `{skill_dir}/criteria/{code}.yaml`,
  `MARKET_SNAPSHOT` = `{WORK_DIR}/00_market_snapshot.md`
- 出力: `{WORK_DIR}/10_rating_{code}.md` + `reports/etf-rating/{code}/{YYYYMMDD}_{code}_rating.md` + `data/etf-rating/history/{code}.jsonl` 追記
- 戻り値: 「{code} 完了（ネット {NN}/100, 前日比 ±N.Npp）」の1行

採点履歴 jsonl の1行スキーマ（参考、詳細は Phase 1 指示書）:
```json
{"date": "20260522", "code": "1629", "net_score": 67.4, "upside_weighted": 71.9,
 "downside_weighted": 37.2, "leading_net": 28.0, "lagging_net": 37.0,
 "criteria_version": "2026-05-22"}
```

### Step 3: Phase 2 集計サマリ

サブエージェント1つ起動。全銘柄レポートを統合し、本日の総評・スコアランキング・
ハイライト（前日比±5pp 超）・観点 version 鮮度警告（90日経過=黄・180日=赤）
を1ファイルにまとめる。

- 指示: `{skill_dir}/agent-instructions/phase2-aggregate.md`
- 入力: `WORK_DIR`, `{WORK_DIR}/10_rating_*.md`, `data/etf-rating/history/*.jsonl`,
  `calc_params.json`
- 出力: `{WORK_DIR}/20_daily_summary.md` + `reports/etf-rating/_daily_summary/{YYYYMMDD}.md`
- 戻り値: 「集計完了（強気 N銘柄 / 警戒 N銘柄）」の1行

### Step 4: Phase 3 メールペイロード生成（`--send-mail` 時のみ）

サブエージェント1つ起動。Phase 2 サマリ + 全銘柄レポートを Jinja2 テンプレで
レンダリングするためのJSONペイロードを生成。実送信は Phase D で実装する
`backend/scripts/etf_rating_send_mail.py` が担当（Phase A 時点ではペイロード
生成までで停止）。

- 指示: `{skill_dir}/agent-instructions/phase3-mail-payload.md`
- 入力: `WORK_DIR`, 全銘柄レポート + サマリ
- 出力: `{WORK_DIR}/email_payload.json`
- 戻り値: 「メールペイロード生成完了（{N}銘柄, {NN}KB）」の1行

Phase A 完了時点ではメイン側で `etf_rating_send_mail.py` を呼ばない（未実装）。
ユーザーに「ペイロードを生成。送信は Phase D で実装予定」と提示して終了。

### Step 5: 完了通知

- 集計サマリのパスをユーザーに提示
- メール送信モードの場合は `email_payload.json` パスも提示

## tune サブコマンド

`/etf-rating tune <code>` は観点（`criteria/{code}.yaml`）の見直し対話を起動する。

- 指示: `{skill_dir}/agent-instructions/tune-criteria.md`
- 動作:
  1. `data/etf-rating/history/{code}.jsonl` 直近30日を読み込み、スコアの
     ボラティリティ・条件別寄与の偏りを集計
  2. 現行 criteria YAML を Read し、追加/削除/閾値調整の提案を AskUserQuestion で順次確認
  3. 承認後、YAML の `revision_history` に追記し `version` を更新（Edit ツール）
- 出力: 更新済み `criteria/{code}.yaml`
- 注意: 自動実行モードでは tune は起動禁止（要対話）

## ファイル構成

```
.claude/skills/etf-rating/
├── SKILL.md
├── calc_params.json
├── agent-instructions/
│   ├── phase0-market-snapshot.md
│   ├── phase1-single-rating.md
│   ├── phase2-aggregate.md
│   ├── phase3-mail-payload.md
│   └── tune-criteria.md
└── criteria/                         # Phase B 以降で作成
    ├── _template.yaml
    └── {code}.yaml                   # 1655 / 314A / 1629 / 1615 / 2646 / 1618 / 200A

{WORK_DIR}/  (= .tmp/etf-rating_YYYYMMDD/)
├── 00_market_snapshot.md             # Phase 0 出力
├── 10_rating_{code}.md               # Phase 1 出力（銘柄ごと）
├── 20_daily_summary.md               # Phase 2 出力
├── email_payload.json                # Phase 3 出力（--send-mail 時のみ）
└── decisions.log                     # 自動実行時のデフォルト選択ログ

reports/etf-rating/
├── {code}/
│   └── {YYYYMMDD}_{code}_rating.md   # 銘柄別レポート（公開先）
└── _daily_summary/
    └── {YYYYMMDD}.md                 # 集計サマリ

data/etf-rating/history/
└── {code}.jsonl                      # 採点履歴（1日1行）
```

## 株価計算の必須ルール

このスキルは現在株価・モメンタム・PER/PBR等を Phase 1 で参照する。
CLAUDE.md「株式分割の管理」セクションを厳守すること:

1. 価格・損益・モメンタムは **必ず API（ChartService 等）経由**で取得
2. SQLite 直接クエリで `trades` / `price_data` を読んで計算に使うことを禁止
3. 対象銘柄の `stock_splits` を事前確認（`is_applied` / `is_chart_applied`）

過去事例: 1629 は 2026-04-01 に 500:1 分割実施済み。生 price_data には
-99.8% の幻のジャンプが残るため、必ず ChartService API で取得すること。

## フェーズ別タイムアウト目安

| Phase | 目標時間 | タイムアウト | 失敗時 |
|-------|----------|--------------|--------|
| Phase 0 | 3分 | 6分 | 中止（Phase 1 で個別検索に縮退も検討） |
| Phase 1（1銘柄） | 5分 | 10分 | 該当銘柄スキップ、他銘柄続行 |
| Phase 2 | 2分 | 5分 | 1回リトライ |
| Phase 3 | 1分 | 3分 | 1回リトライ |
| 全銘柄並列 | 30分以内 | 40分 | 残銘柄スキップしメール送信 |

## フォールバックポリシー

| 失敗条件 | 対応 |
|----------|------|
| Phase 0 失敗 | 警告して続行（Phase 1 は内部で簡易検索） |
| Phase 1 一部銘柄失敗 | 該当銘柄を「データ取得不可」マークで集計に含める |
| Phase 1 全銘柄失敗 | スキル全体を中止 |
| criteria YAML 欠損 | 該当銘柄スキップ、サマリに警告 |
| Web 検索レート制限 | calc_params.json の検索バジェットで自動抑制 |

## 完了条件（Phase A）

- [ ] SKILL.md / agent-instructions 5本 / calc_params.json が作成済み
- [ ] `/etf-rating 1629` が手動で動く（メール送信なしの単一銘柄評価）
- [ ] 自動実行時に AskUserQuestion をスキップする分岐が動作
- [ ] `criteria/{code}.yaml` 不在時は明示的にエラーで停止（Phase B で投入予定）
