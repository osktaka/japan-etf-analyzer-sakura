---
name: portfolio-analysis-v2
description: ポートフォリオ分析 v2（ブレインストーミング方式）
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Task, TaskOutput, WebSearch, WebFetch, AskUserQuestion, Write
aliases: ["/pf-v2", "/portfolio-analysis-v2"]
---

# ポートフォリオ分析 v2（ブレインストーミング方式）

## 概要

v1の portfolio-analysis をブレインストーミング方式で再構築したスキル。3つの専門会議（各4名 = 計12名の固定キャラクター）が並列で議論し、マージ会議で統合してレポートを生成する。プロのアナリスト視点で客観的に分析する。

- モード指定なし（常にフルモード）
- v1と共存: `/pf-analysis` = v1、`/pf-v2` = v2

## コンテキスト管理ルール

### 作業ディレクトリ

```bash
SESSION_ID=$(date +%Y%m%d_%H%M%S)_$(openssl rand -hex 2)
WORK_DIR=".tmp/pf2_${SESSION_ID}"
mkdir -p "${WORK_DIR}"
```

### データ受け渡しルール

| ルール | 説明 |
|--------|------|
| ファイルベース通信 | 全中間データは `WORK_DIR` 内のファイルに保存 |
| 要約のみ返却 | サブエージェントはメインに1-2行の完了報告のみ返す。データ全文返却禁止 |
| メインはReadしない | メインエージェントはPhaseの中間ファイルをReadしない（パスのみ管理） |

### メインエージェントの制約

- `agent-instructions/` 配下のファイルは**メインエージェントが読み込まない**
- メインはサブエージェントのプロンプトに**指示ファイルパスとパラメータ**を渡すだけ
- サブエージェントが自分の指示ファイルを直接読み込んで実行する

### コンテキスト最適化（30分目標達成のための必須事項）

**Phase 1 エージェント向け読み込みルール**:
- Phase 1-1（リスク・リターン）: `05_shared_calculations.md` と `0a_market_environment.md` のみ読む。`0b_trend_summary.md` は不要
- Phase 1-2（分散）: `05_shared_calculations.md` と `00_portfolio_data.json`（tag_dataのみ）と `0a_market_environment.md` を読む
- Phase 1-3（品質）: `05_shared_calculations.md` と `00_portfolio_data.json`（holdings, recommendations）を読む
- **禁止**: Phase 1エージェントが `20_merge_meeting.md` を参照すること（存在しない段階のため当然だが明示）

**Phase 2 エージェント向け読み込みルール**:
- `10_meeting_risk_return.md`, `10_meeting_allocation.md`, `10_meeting_quality.md` を読む
- ただし**各ファイルの「## 議事録」セクション以降のみ**読む（会議トランスクリプト全文は不要）
- `05_shared_calculations.md` の「計算メタデータ」セクションのみ参照（詳細計算は不要）

**Phase 3 エージェント向け読み込みルール**:
- `20_merge_meeting.md` の「📋 Phase 3向け洞察エクスポート」セクション（末尾）と「## 統合議事録」セクションのみ読む
- `05_shared_calculations.md` は各セクションヘッダーを確認して必要な節のみ読む（全文読み込み禁止）
- `00_portfolio_data.json` は `_metadata`, `summary`, `holdings` キーのみ参照
- **report-guide.md は最初の30行（セクション一覧）のみ読んでから、必要なセクションを個別に読む**

**コンテキスト節約の効果試算**:
- Phase 2の全会議録読み込み削減: 約30,000字 → 約6,000字（-80%）
- Phase 3のデータ読み込み削減: 約20,000字 → 約8,000字（-60%）

## フェーズ別タイムアウト設定

| フェーズ | 目標時間 | タイムアウト | 超過時の対応 |
|---------|---------|-----------|-----------|
| Phase 0（データ収集） | 3分 | 5分 | 中止・メインに報告 |
| Phase 0a（市場環境） | 2分 | 4分 | フォールバック値で続行 |
| Phase 0b（トレンド） | 1分 | 3分 | スキップして続行 |
| Phase 0.5（定量計算） | 4分 | 7分 | 中止・メインに報告 |
| Phase 1（各会議×3） | 5分 | 8分 | 警告して2会議でマージへ |
| Phase 2（マージ会議） | 5分 | 8分 | 1回リトライ |
| Phase 3（レポート生成） | 3分 | 6分 | 1回リトライ |
| **合計（並列考慮後）** | **~25分** | **~35分** | — |

**注意**: 上記は単一エージェント処理時の目安。並列実行（Step 1の3並列、Phase 1の3並列）により実際の経過時間は短縮される。

## キャラクター定義（12名、固定）

### 会議1: リスク・リターン効率

| タイプ | 名前 | 役割 |
|--------|------|------|
| 天才 | 高橋 誠一 | リスク管理の第一人者。VaR/CVaR/最大DDを駆使し、効率フロンティア上の最適位置を見極める |
| 初心者 | 佐藤 あゆみ | 投資を始めたばかりの会社員。「リスクって具体的にいくら損する可能性？」と素朴に問う |
| ポジティブ | 田中 健太 | グロース投資家。リスクを取ることで得られるリターンの機会を強調する実践者 |
| 心配性 | 山田 慎二 | リスク管理委員。最悪シナリオを常に想定し、守りの戦略を提案 |

### 会議2: 分散・アロケーション

| タイプ | 名前 | 役割 |
|--------|------|------|
| 天才 | 鈴木 理恵 | アセットアロケーション専門家。相関行列と効率的分散を追求するストラテジスト |
| 初心者 | 中村 大輔 | 分散投資を学び始めた新人。「同じ日本株ETFでも分散になるの？」と本質的な疑問を投げる |
| ポジティブ | 伊藤 美咲 | グローバル投資家。足りないアセットクラスの追加機会を提案する |
| 心配性 | 渡辺 正人 | 集中リスクを心配するアナリスト。特定セクター/地域への偏りを厳しく指摘 |

### 会議3: 銘柄品質・入替判断

| タイプ | 名前 | 役割 |
|--------|------|------|
| 天才 | 小林 哲也 | バリュー投資のプロ。5軸スコアとファンダメンタルズから本質的価値を見極める |
| 初心者 | 加藤 さくら | ETF選びに迷う投資初心者。「このETFと似たものの違いは？」と比較視点で問う |
| ポジティブ | 松本 翔太 | テクニカル分析家。モメンタムと出来高トレンドから上昇機会を見出す |
| 心配性 | 藤田 恵子 | 損切りに慎重なアナリスト。含み損銘柄の継続保有リスクを指摘 |

## 実行フロー

`{skill_dir}` = `.claude/skills/portfolio-analysis-v2`

### Step 0: 初期化

1. WORK_DIR を作成（上記 bash 参照）
2. AskUserQuestion で対象ユーザーIDを聞く（デフォルト: demo）。例: 「分析対象のユーザーIDを入力してください（デフォルト: demo）」
3. timing.json を初期化:

```json
{
  "session_id": "{SESSION_ID}",
  "phases": {},
  "total_duration_sec": null
}
```

### Step 1: データ収集（3並列）

3つの Task を全て `run_in_background: true` で同時起動する。

| Phase | subagent_type | 指示ファイル | 依存 |
|-------|--------------|------------|------|
| 0a（市場環境） | general-purpose | `{skill_dir}/agent-instructions/phase0a-market-research.md` | なし |
| 0（APIデータ） | general-purpose | `{skill_dir}/agent-instructions/phase0-data-collection.md` | なし |
| 0b（トレンド） | general-purpose | `{skill_dir}/agent-instructions/phase0b-trend-summary.md` | HISTORY.md読み込み |

**プロンプト例（各共通）**:
```
以下の指示ファイルをReadして実行してください:
{skill_dir}/agent-instructions/phase0x-xxx.md

パラメータ:
- WORK_DIR: {WORK_DIR}
- USER_ID: {USER_ID}（Phase 0のみ）

メインへの戻り値は完了報告1行のみ。
```

**プレースホルダー置換**: `{skill_dir}`, `{WORK_DIR}`, `{USER_ID}` を実値に置換してからサブエージェントに渡す。

### Step 2: 定量計算

**開始条件**: Phase 0 AND Phase 0a の**両方が完了後**に起動する。
（Phase 0aのRf値を確実に取得するために必須。Phase 0bの完了は待たない）

- Task(general-purpose)
- 指示: `{skill_dir}/agent-instructions/phase05-shared-calculations.md` をReadし実行
- 入力: `{WORK_DIR}/00_portfolio_data.json` + `{WORK_DIR}/0a_market_environment.md`
- 出力: `{WORK_DIR}/05_shared_calculations.md`
- 戻り値: 「共通定量計算完了（Rf取得元: {出典URL or フォールバック}, Rf値: {X.XX}%）」の1行のみ

**timing.json への記録**（Phase 0.5完了後にメインが更新）:
- `Rf_source`: 取得元URL（mof.go.jp/boj.or.jp）またはフォールバック
- `Rf_value`: 使用したリスクフリーレート値（%）

**⚡ 30分目標達成のポイント**: Step 1の3並列（Phase 0 / 0a / 0b）は同時起動が絶対条件。
Phase 0とPhase 0aが揃い次第（Phase 0bを待たずに）Step 2を開始すること。

### Step 3: 3並列ブレインストーミング（Phase 1）

**開始条件**: Phase 0.5 完了後に起動する（Phase 0aはStep 2で既に完了済みのため待機不要）。

3つの Task を全て `run_in_background: true` で同時起動する。

| 会議 | MEETING_ID | type | 出力ファイル |
|------|-----------|------|------------|
| 会議1: リスク・リターン効率 | 1 | risk-return | `{WORK_DIR}/10_meeting_1.md` |
| 会議2: 分散・アロケーション | 2 | allocation | `{WORK_DIR}/10_meeting_2.md` |
| 会議3: 銘柄品質・入替判断 | 3 | quality | `{WORK_DIR}/10_meeting_3.md` |

**プロンプト**:
```
以下の指示ファイルをReadして実行してください:
1. {skill_dir}/agent-instructions/phase1-meeting-common.md（共通ルール）
2. {skill_dir}/agent-instructions/phase1-meeting-{type}.md（固有指示）

パラメータ:
- WORK_DIR: {WORK_DIR}
- MEETING_ID: {1|2|3}

メインへの戻り値は完了報告1行のみ。
```

### Step 4: マージ会議（Phase 2）

**開始条件**: 3会議のうち **2つ以上** が完了後に起動。

- Task(general-purpose)
- 指示: `{skill_dir}/agent-instructions/phase2-merge-meeting.md` をRead
- 入力: 完了した会議ファイル + `{WORK_DIR}/05_shared_calculations.md` + `{WORK_DIR}/0a_market_environment.md`
- 出力: `{WORK_DIR}/20_merge_meeting.md`
- 戻り値: 「マージ会議完了」の1行のみ

### Step 5: レポート生成（Phase 3）

- Task(general-purpose)
- 指示: `{skill_dir}/agent-instructions/phase3-report-integration.md` をRead
- 入力: `{WORK_DIR}/20_merge_meeting.md` + 生データ（`00_portfolio_data.json`等） + `{skill_dir}/report-guide.md`
- 出力: `reports/{USER_ID}/YYYYMMDD_{USER_ID}_v2.md`
- 戻り値: 「レポート保存完了: reports/{USER_ID}/YYYYMMDD_{USER_ID}_v2.md」の1行のみ

### Step 6: 完了通知

- レポートパスをユーザーに提示
- timing.json の集計結果を表示

## ファイル構成

```
{WORK_DIR}/
├── 0a_market_environment.md     # Phase 0a出力
├── 0b_trend_summary.md          # Phase 0b出力
├── 00_portfolio_data.json       # Phase 0出力
├── 05_shared_calculations.md    # Phase 0.5出力
├── 10_meeting_1.md              # Phase 1: 会議1（リスク・リターン効率）
├── 10_meeting_2.md              # Phase 1: 会議2（分散・アロケーション）
├── 10_meeting_3.md              # Phase 1: 会議3（銘柄品質・入替判断）
├── 20_merge_meeting.md          # Phase 2: マージ会議
└── timing.json                   # 実行時間記録
```

## 分析で活用するデータソース

| データソース | テーブル/API | 用途 |
|-------------|-------------|------|
| 保有銘柄 | PortfolioService.get_holdings(user_id) | 分割調整済み保有データ（**必ずサービス層経由。SQLite直接クエリ禁止**） |
| ポートフォリオサマリー | PortfolioService.get_portfolio_summary(user_id) | 総資産、含み損益 |
| パフォーマンスキャッシュ | AnalysisDataService.get_analysis_data() | 8期間リターン、ボラティリティ、回帰上昇率 |
| スコアキャッシュ | AnalysisDataService.get_analysis_data() | 5軸スコア x 6視点 |
| 勢いラベル | AnalysisDataService.get_analysis_data() | 5段階モメンタム |
| 日次価格履歴 | AnalysisDataService.get_analysis_data() | 相関分析用（月次リターン） |
| 資産推移 | PortfolioService.get_valuation_history(user_id, '3y') | 最大ドローダウン、回復期間 |
| 比較API | CompareService.get_comparison(codes) | 銘柄間比較 |
| おすすめAPI | RecommendService.get_recommendations(perspective) | 代替銘柄候補 |
| タグ情報 | AnalysisDataService.get_analysis_data() | セクター/地域/テーマ分類 |
| ETF詳細 | AnalysisDataService.get_analysis_data() | 信託報酬、配当利回り、純資産、運用会社 |
| 市場環境調査 | WebSearch + WebFetch | 主要指標・政治経済トピック |

## フォールバックポリシー

| フェーズ | 失敗条件 | 対応 |
|---------|---------|------|
| Phase 0（データ収集） | DB接続失敗 or holdings取得失敗 | **スキル全体を中止** |
| Phase 0a | 市場環境取得失敗 | 警告して続行（市場環境なしで分析） |
| Phase 0b | トレンドサマリー失敗 | 警告して続行 |
| Phase 0.5 | 定量計算失敗 | **スキル全体を中止** |
| Phase 1 | 3会議中2つ以上失敗 | **スキル全体を中止** |
| Phase 1 | 3会議中1つ失敗 | 警告して2会議でマージに進む |
| Phase 2 | マージ会議失敗 | 1回リトライ。失敗時は個別会議結果でレポート生成 |
| Phase 3 | レポート生成失敗 | 1回リトライ。失敗時はマージ結果ファイルを最終成果物として提示 |

**メインエージェントの判断フロー**:
1. 各フェーズのサブエージェント完了後、出力ファイルの存在を確認
2. 上記テーブルに従い続行/中止を判断
3. 中止時はユーザーにエラー内容と推奨アクションを報告

## timing.json 仕様

```json
{
  "session_id": "20260312_143000_abc1",
  "rf_source": "https://www.mof.go.jp/...",
  "rf_value": 1.32,
  "phases": {
    "phase_0a": {"start": "ISO8601", "end": "ISO8601", "duration_sec": 120},
    "phase_0": {"start": "...", "end": "...", "duration_sec": 180},
    "phase_0b": {"start": "...", "end": "...", "duration_sec": 60},
    "phase_05": {"start": "...", "end": "...", "duration_sec": 90},
    "phase_1_meeting_1": {"start": "...", "end": "...", "duration_sec": 300},
    "phase_1_meeting_2": {"start": "...", "end": "...", "duration_sec": 300},
    "phase_1_meeting_3": {"start": "...", "end": "...", "duration_sec": 300},
    "phase_2": {"start": "...", "end": "...", "duration_sec": 240},
    "phase_3": {"start": "...", "end": "...", "duration_sec": 120}
  },
  "total_duration_sec": 900
}
```

- `rf_source`: Phase 0.5完了後にメインが記録。URLまたは「フォールバック（0.50%）」
- `rf_value`: 使用したRf値（数値, %単位）。フォールバック時は `0.50`

各フェーズの start/end はサブエージェント起動時刻/完了時刻をメインエージェントが記録する。

## 重要注意事項

### 株式分割対策

DBの trades テーブルは分割前の元の数量・単価で記録されている。**必ずサービス層（PortfolioService）経由で分割調整済みデータを取得すること**。SQLite直接クエリは株式分割が反映されない。

**既知の障害（2026-02-14）**: Phase 0で一部銘柄の数量・取得単価が分割調整前データで収集され、総資産が約3万円過小評価。レポート全体が破棄に至った。

### Phase 0 テンプレート使用義務

Phase 0 のデータ収集は `phase0-collection-template.py` をベースに実行すること。独自スクリプトの新規作成は禁止。テンプレートには株式分割調整データの整合性検証が組み込まれている。

### プレースホルダー置換

サブエージェントへのプロンプトでは、以下を実値に置換してから渡す:
- `{skill_dir}` → `.claude/skills/portfolio-analysis-v2`
- `{WORK_DIR}` → 実際の作業ディレクトリパス
- `{USER_ID}` → 対象ユーザーID（AskUserQuestionで取得した値）

### 市場指標の取得タイミング

Phase 0a で取得する市場指標は**当日の終値または直前営業日の終値**を使用する。取引時間中の実行時は前営業日の終値を使用し、その旨をレポートに明記する。

## 完了条件

- [ ] 市場環境情報を収集した（Phase 0a）
- [ ] 全データソースを取得した（Phase 0）
- [ ] 共通定量計算を実施した（Phase 0.5）
- [ ] 3つのブレインストーミング会議を実施した（Phase 1）
- [ ] マージ会議で統合した（Phase 2）
- [ ] レポートファイルが `reports/{USER_ID}/` に保存された（Phase 3）
- [ ] timing.json が全フェーズの実行時間を記録している
