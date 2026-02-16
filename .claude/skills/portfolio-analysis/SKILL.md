# ポートフォリオ定量分析スキル

```yaml
---
name: portfolio-analysis
description: ポートフォリオ定量分析・最適化（システム全データ活用）
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Task, WebSearch, WebFetch, AskUserQuestion, Write
aliases: ["/portfolio-analysis", "/pf-analysis"]
---
```

## 概要

このスキルは、ユーザーのETFポートフォリオをシステムが保持する全データを活用して定量分析し、最適化提案を行うワークフロー。エージェントチーム（3名体制）で並行分析→クロスレビュー→統合レポートを作成する。

## コンテキスト管理ルール

メインエージェントのコンテキスト消費を最小化するため、以下のルールを厳守する。

### 作業ディレクトリ

スキル実行開始時に、セッション固有の作業ディレクトリを作成する:

```bash
SESSION_ID=$(date +%Y%m%d_%H%M%S)_$(openssl rand -hex 2)
WORK_DIR=".tmp/pf_${SESSION_ID}"
mkdir -p "${WORK_DIR}"
```

- Docker内: `/app/${WORK_DIR}`
- ホスト側: `{project_root}/${WORK_DIR}`
- 全サブエージェントにこの `WORK_DIR` を渡す

### データ受け渡しルール

| ルール | 説明 |
|--------|------|
| ファイルベース通信 | 全ての中間データは `WORK_DIR` 内のファイルに保存する |
| 要約のみ返却 | サブエージェントはメインに1-2行の完了報告のみ返す。分析結果・データの全文を返さない |
| 統合エージェント | Phase 3のレポート作成はメインが行わず、統合エージェントがファイルから直接読み込んで作成する |
| 禁止事項 | サブエージェントがJSONデータの全体や分析テーブル全文をメインへの戻り値に含めること |

### ツール使用制約

| ルール | 説明 |
|--------|------|
| TaskOutput blocking必須 | TaskOutput は blocking モード（デフォルト）のみ使用する。non-blocking（block=false）による進捗ポーリングは禁止（コンテキスト消費の無駄） |
| timing.json バッチ更新 | timing.json の更新は Phase 1完了後の一括書き込み1回のみ（初期化は WORK_DIR作成と同時）。フェーズ毎の個別更新は禁止 |

### メインエージェントの制約

- `agent-instructions/` 配下のファイルは**メインエージェントが読み込まない**
- メインはサブエージェントのプロンプトに**指示ファイルパスとWORK_DIR**を渡すだけ
- サブエージェントが自分の指示ファイルを直接読み込んで実行する

### ファイル構成

詳細は `./execution-details.md` の「ファイル構成」を参照。主要な出力ファイル: `portfolio_data.json`, `portfolio_reference.md`, `*_analysis.md`, `timing.json`

## モード選択

スキル実行開始時に、AskUserQuestionツールで分析モードをユーザーに確認する。

**質問**: 「分析モードを選択してください」
**ヘッダー**: 「分析モード」
**選択肢**:

| モード | ラベル | 説明 | 所要時間目安 |
|-------|-------|------|------------|
| speed | 速度重視 | タスクを分割して並行実行。クロスレビューなし。最短時間で結果を得る | 5-10分 |
| normal | ノーマル（推奨） | タスク分割＋並行実行＋クロスレビュー1回。バランス重視 | 10-15分 |
| debate | 議論重視 | 複数エージェントが同じデータを独立分析→議論→ブラッシュアップ。最も深い洞察 | 20-30分 |

### モード別実行フロー

#### 速度重視（speed）

Phase 0a + Phase 0 + Phase 0b（並行）→ Phase 1（タスク分割型並行、3エージェント別タスク）→ Phase 3+4（統合、クロスレビューなし）

- クロスレビューを完全スキップ。セクション9は「速度重視モードのためスキップ」と記載

#### ノーマル（normal）

Phase 0a + Phase 0 + Phase 0b（並行）→ Phase 1（タスク分割型並行、3エージェント別タスク）→ Phase 3+4（統合、クロスレビュー含む）

- クロスレビューは統合エージェント内で実施（独立フェーズではない）

#### 議論重視（debate）

Phase 0a + Phase 0 + Phase 0b（並行）→ Phase 0.5（共通定量計算）→ Phase 1（ペルソナ別独立分析）→ Phase 3（クロスレビュー2ラウンド）→ Phase 4（統合）

- Phase 0.5で決定論的な計算結果（シャープレシオ、相関係数、ドローダウン等）を `shared_calculations.md` に出力
- Phase 1では3エージェントが**同じ全データ+共通計算結果**を受け取り、ペルソナごとの解釈・見解・提言を独立に行う
- クロスレビュー（2ラウンド: 相互レビュー→反論→合意形成）はPhase 3で独立エージェントが実施し、Phase 4で統合
- レポートのセクション9に議論の経緯を詳細に記載

**議論重視モードのペルソナ構成**:

3つの異なる視点を持つペルソナが独立分析→クロスレビュー→合意形成を行うことで、単一視点では見落としがちなリスクや機会を多角的に発見する。

| ペルソナ | 役割 | 推論手法 | 重視する観点 |
|---------|------|---------|------------|
| analyst-A: 積極派 | 成長機会の最大化 | 機会探索型推論（トレンド→成長ポテンシャル→アクション） | モメンタム・シャープレシオ・低スコア銘柄入替 |
| analyst-B: 堅実派 | 資産保全と安定運用 | 保守的推論（リスク→回避策→安全マージン確保） | ドローダウン・ストレスシナリオ・現金比率 |
| analyst-C: 異論派 | 見落とされた視点の掘り起こし | 反証主義的推論（結論→反例探索→盲点の発見） | 相関・タグ分散・運用会社集中リスク |

## 分析で活用するデータソース

| データソース | テーブル/API | 用途 |
|-------------|-------------|------|
| 保有銘柄 | GET /api/v1/portfolio/holdings | 分割調整済み保有データ（**必ずAPI経由で取得。SQLite直接クエリは株式分割が反映されない**） |
| ポートフォリオサマリー | GET /api/v1/portfolio | 総資産、含み損益 |
| パフォーマンスキャッシュ | performance_cache テーブル | 8期間リターン、ボラティリティ、回帰上昇率 |
| スコアキャッシュ | score_cache テーブル | 5軸スコア（配当力/コスト効率/規模信頼性/売買品質/リターン）× 6視点 |
| 勢いラベル | etfs.momentum_label | 上昇加速〜下降加速の5段階 |
| 日次価格履歴 | price_histories テーブル | 相関分析用（月次リターン計算） |
| 資産推移 | GET /api/v1/portfolio/valuation-history?period=3y | 最大ドローダウン、回復期間 |
| 比較API | GET /api/v1/compare/performance, /scores | 銘柄間パフォーマンス・スコア比較 |
| おすすめAPI | GET /api/v1/recommendations?perspective=... | 代替銘柄候補（balance, dividend, low-cost視点） |
| タグ情報 | etf_tag_relations + tags テーブル | セクター/地域/テーマ分類 |
| ETF詳細 | etfs テーブル | 信託報酬、配当利回り、純資産、運用会社、上場日 |
| 現金残高 | summaryのcash_balance（PortfolioService経由） | 現金比率算出 |
| 市場環境調査 | WebSearch + WebFetch | 主要指標・政治経済トピック・分析への示唆 |

## 重要な注意事項

### Phase 0テンプレート使用義務（最優先）

Phase 0のデータ収集は、**必ず** `phase0-collection-template.py` をベースに実行すること。独自スクリプトの新規作成は禁止。テンプレートには以下の障害対策が組み込まれている:
- 株式分割調整データの整合性検証（quantity × current_price = current_value）
- 総資産の照合（銘柄合計 + 現金 = サマリー総資産）
- `_metadata` / `_data_status` の自動生成

**違反時のリスク**: 2026-02-14に発生した総資産約3万円の過小評価（レポート全体破棄）の再発。

### フェーズレベルの失敗時フォールバックポリシー

詳細は `./execution-details.md` の「フェーズレベルの失敗時フォールバックポリシー」を参照。要点:
- Phase 0の認証/holdings失敗、Phase 1の2体以上失敗は**スキル全体を中止**
- Phase 0a失敗は市場環境なしで続行可
- 各フェーズ完了後、出力ファイルの存在を確認して続行/中止を判断

### データ不十分時のスキップ判断

Phase 1完了後にメインエージェントが確認する。詳細は `./data-skip-rules.md` を参照。スキップ前に `_metadata` の確認が必須。`_metadata` を確認せずに「データ不足」と判断することは禁止。

### 株式分割の取り扱い

**警告**: DBの生の取引データ（tradesテーブル）は分割前の元の数量・単価で記録されている。正確な損益はPortfolioService（API）経由で取得すること。

- 保有銘柄データは **必ずAPI経由** で取得
- SQLiteに直接クエリすると分割前のデータが返される
- 詳細はCLAUDE.mdの「株式分割の管理」セクションを参照

**既知の問題（2026-02-14発生）**: Phase 0のデータ収集で、一部銘柄（1615/1489/1597）の数量・取得単価が分割調整前のデータで収集され、総資産が約3万円過小評価された。レポート全体が不正確となり破棄に至った。`phase0-data-collection.md` に追加した検証ステップを必ず実行すること。

### 市場指標の取得タイミング

**重要**: Phase 0aで取得する市場指標（日経平均、TOPIX、ドル円、S&P500等）は、取引時間中の値ではなく**当日の終値または直前営業日の終値**を使用すること。

- 取引時間中に実行する場合は、前営業日の終値を使用し、その旨をレポートに明記する
- WebSearchで「○○ 終値 YYYY年M月D日」のようにクエリを工夫して確定値を取得する
- 取引時間中の値（リアルタイム値）と終値では数百円〜数千円の差が出る場合がある
- レポートの市場環境サマリーには、指標の取得日時を明記する

### APIアクセス方法

Docker環境内からcurl（またはPython requests）でアクセス。認証にはログインしてセッションCookieを使用。

```bash
# Docker環境内からAPIにアクセス
docker compose exec backend python -c "
import requests
session = requests.Session()
session.post('http://localhost:8902/api/v1/auth/login',
  json={'user_id': '{USER_ID}', 'password': '{PASSWORD}'})
resp = session.get('http://localhost:8902/api/v1/portfolio/holdings')
print(resp.json())
"
```

※テストユーザーの認証情報はCLAUDE.mdの「テストユーザー」セクションを参照。

## 実行フロー

### 実行時間計測

メインエージェントは `{WORK_DIR}/timing.json` に実行時間を記録する。

**メインの記録タイミング（2回のみ）**:
1. WORK_DIR作成時: `skill_start` とセッションJSONLの現在行数を記録（mkdir と同一Bashコマンド内）
2. Phase 1完了後: 中間ファイルの更新時刻（`stat`）から各フェーズの完了時刻を取得し一括書き込み

**Phase 3/4のtiming**: Phase 3+4オーケストレーター（debateモード）または統合エージェント（speed/normalモード）が内部で記録。

**timing.json 初期化**: WORK_DIR作成と同時に `skill_start` に加え、セッションJSONLの情報を記録する:
```bash
PROJECT_HASH=$(pwd | sed 's|/|-|g' | sed 's/^-//')
SESSION_JSONL=$(ls -t ~/.claude/projects/${PROJECT_HASH}/*.jsonl 2>/dev/null | head -1)
SESSION_START_LINE=$(wc -l < "$SESSION_JSONL" 2>/dev/null || echo "0")
```

timing.json の初期値:
```json
{
  "skill_start": "2026-02-15T10:00:00",
  "session_jsonl_path": "/home/t_osaka/.claude/projects/.../<session>.jsonl",
  "session_jsonl_start_line": 12345
}
```

**一括書き込みコード例**:
```bash
python3 -c "
import json, os, datetime
wd = '{WORK_DIR}'
def mtime(f):
    try: return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(wd, f))).isoformat()
    except: return None
with open(os.path.join(wd, 'timing.json')) as f:
    data = json.load(f)
updates = {
    'phase_0a_end': mtime('market_environment.md'),
    'phase_0b_end': mtime('trend_summary.md'),
    'phase_0_end': mtime('portfolio_data.json'),
    'phase_05_end': mtime('shared_calculations.md'),
    'phase_1_end': datetime.datetime.now().isoformat()
}
data.update({k:v for k,v in updates.items() if v})
with open(os.path.join(wd, 'timing.json'), 'w') as f:
    json.dump(data, f, indent=2)
print('timing updated')
"
```

**注意**: 各フェーズの `_start` イベントは精度が低下するため記録しない。`_end` イベントのみファイル更新時刻から取得する。

### Phase 0a: 市場環境調査（general-purposeエージェントに委譲）

レポートの冒頭に掲載する「市場環境サマリー」の情報を収集する。**general-purposeサブエージェント**に委譲し、Phase 0と並行実行する。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase0a-market-research.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- **メインへの戻り値は「市場環境調査完了」の1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。サブエージェントが直接読み込む。

### Phase 0b: トレンドサマリー生成（general-purposeエージェントに委譲）

過去の分析履歴（metrics.json）とHISTORY.mdから、資産推移・スコア推移・アクション実行状況等のトレンドサマリーを生成する。**general-purposeサブエージェント**に委譲し、Phase 0/0aと並行実行する。

**当該実行のPhase 0出力（portfolio_data.json等）には依存しない**。過去の蓄積データのみを入力とする。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase0b-trend-summary.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- 対象ユーザー: `{USER_ID}`（user_id。`reports/{USER_ID}/` のパス構築に使用）
- **メインへの戻り値は「トレンドサマリー完了」の1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。サブエージェントが直接読み込む。

### Phase 0: データ収集（Bashエージェントに委譲）

以下のデータを一括取得し、`{WORK_DIR}/portfolio_data.json` に保存する。対象銘柄はAPI取得後の保有銘柄リストから動的に決定。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase0-data-collection.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- 対象ユーザー: `{USER_ID}`（user_id）、パスワード: `{PASSWORD}`
- **メインへの戻り値は「データ収集完了: N銘柄、総評価額XXX万円」の要約1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。サブエージェントが直接読み込む。

**テンプレート使用必須**: `{skill_dir}/agent-instructions/phase0-collection-template.py` をベースとしてスクリプトを作成すること。独自の新規スクリプト作成は禁止（2026-02-14障害対応）。

**収集データリスト**（メインの完了確認用）:
1. APIからポートフォリオデータ取得（ログイン → holdings → summary）
2. performance_cache（全保有銘柄の8期間リターン・ボラティリティ・回帰率）
3. score_cache（全保有銘柄の5軸×6視点スコア）
4. etfs（momentum_label, manager, listing_date, deviation_rate）
5. 月次価格データ（price_histories、直近13ヶ月の月初価格）
6. 資産推移API（valuation-history?period=3y）
7. タグ情報（etf_tag_relations JOIN tags）
8. おすすめ銘柄API（balance, dividend, low-cost の各視点トップ10）
9. 比較API（保有銘柄同士のperformance, scores）
10. `portfolio_reference.md`の生成（セクション1・11.2用のmarkdownテーブルをPythonで自動生成。Phase 4統合エージェントがレポート作成時にこのファイルの表を読み込んで挿入する）

### Phase 0.5: 共通定量計算（debateモード限定）

**開始条件**: Phase 0aとPhase 0の**両方が完了**してから起動する。
**実行条件**: debateモードのみ。speed/normalモードでは実行しない。

決定論的な計算（シャープレシオ、相関係数、ドローダウン等）を1エージェントで実行し、Phase 1の3ペルソナエージェントが計算を重複実行することを防ぐ。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase05-shared-calculations.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- skill_dir: `{skill_dir}`
- **メインへの戻り値は「共通定量計算完了」の1行のみ**

### Phase 1: 並行分析（並列Task）

**開始条件**: Phase 0aとPhase 0の**両方が完了**してからPhase 1を起動する。debateモードの場合は、さらにPhase 0.5の完了も必要。

Taskツールで複数のサブエージェントを**同一ターンで並列発行**する。エージェント間通信は不要（ファイルベース通信のみ）。

**サブエージェントへの指示方法**: 各サブエージェントのプロンプトに指示ファイルパスとWORK_DIRを渡す。**メインエージェントは指示ファイルの内容を読み込まない**。

**共通指示**: 議論重視モードの各エージェント（analyst-A/B/C）は、個別指示ファイルの前に `{skill_dir}/agent-instructions/phase1-debate-common.md` を先に読み込むこと。

#### 速度重視・ノーマルモード: タスク分割型

3エージェントがそれぞれ**異なるタスク**を並行実行。

| エージェント | 指示ファイル | 出力ファイル |
|-------------|------------|------------|
| quant-analyst | `{skill_dir}/agent-instructions/phase1-quant-analyst.md` | `{WORK_DIR}/quant_analysis.md` |
| score-analyst | `{skill_dir}/agent-instructions/phase1-score-analyst.md` | `{WORK_DIR}/score_analysis.md` |
| allocation-analyst | `{skill_dir}/agent-instructions/phase1-allocation-analyst.md` | `{WORK_DIR}/allocation_analysis.md` |

**注意**: allocation-analystは常に起動。5銘柄未満の場合は項目A(地域別)/B(セクター別)/C(テーマ別)/F(集中度ヒートマップ)をスキップし、D(欠落アセットクラス)/E(現金比率)のみ実施。

#### 議論重視モード: 独立分析型

**常に3体起動**。3エージェントが**同じ全データ**を受け取り、それぞれ独立に全項目を分析。

| エージェント | 指示ファイル | 出力ファイル |
|-------------|------------|------------|
| analyst-A | debate-common + quant + score + allocation（4ファイル） | `{WORK_DIR}/analyst_a_analysis.md` |
| analyst-B | 同上 | `{WORK_DIR}/analyst_b_analysis.md` |
| analyst-C | 同上 | `{WORK_DIR}/analyst_c_analysis.md` |

各エージェントは自分なりの優先順位付け・総合判断を行い、最終的に統合エージェントが合意形成する。

### クロスレビュー

- **速度重視モード**: クロスレビューなし（セクション9は「速度重視モードのためスキップ」と記載）
- **ノーマルモード**: 統合エージェント内で実施。統合エージェントが `{skill_dir}/agent-instructions/crossreview-normal.md` を参照
- **議論重視モード**: Phase 3として独立実行。メインエージェントが3エージェントによる2ラウンドのクロスレビューをオーケストレーション（詳細は「Phase 3: クロスレビュー」セクション参照）。統合エージェントは `{skill_dir}/agent-instructions/crossreview-debate.md`（統合ガイド）を参照して結果を統合

### Phase 3+4: オーケストレーター委譲（debateモード限定）

**実行条件**: debateモードのみ。speed/normalモードでは Phase 3+4 統合エージェントを直接起動（従来通り）。
**開始条件**: Phase 1の3エージェント全員が完了し、timing.json一括書き込みが完了してから起動する。

debateモードでは、Phase 3（クロスレビュー2ラウンド）+ Phase 4（統合レポート）を **1体のgeneral-purposeサブエージェント（オーケストレーター）** に委譲する。メインエージェントのコンテキスト消費を抑制するため、Phase 3+4の全てのTask起動・待機・ファイル確認をオーケストレーター内で完結させる。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase34-debate-orchestrator.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- mode: `debate`
- skill_dir: `{skill_dir}`
- 対象ユーザー: `{USER_ID}`（レポートファイル名 `YYYYMMDD_{USER_ID}.md` および `reports/{USER_ID}/` パス構築に使用）
- **メインへの戻り値は「Phase 3+4完了: ./reports/{USER_ID}/YYYYMMDD_....md」の1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。オーケストレーターが直接読み込む。

### Phase 4: 統合レポート作成・保存（統合エージェントに委譲）

**debateモード**: Phase 4はPhase 3+4オーケストレーターが起動するため、メインエージェントは直接起動しない。以下はspeed/normalモードの場合の手順。

レポートの作成・保存はメインエージェントが行わず、**統合エージェント（general-purpose）**に委譲する。

- **speed/normalモード**: Phase 1の分析結果を統合し、クロスレビュー（normalの場合）も統合エージェント内で実施
- **debateモード**: Phase 1の分析結果 + Phase 3のクロスレビュー結果を読み込み、レポートに統合（クロスレビュー自体はPhase 3で完了済み）

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase34-integration.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- モード: `{mode}`（speed/normal/debate）
- skill_dir: `{skill_dir}`
- 対象ユーザー: `{USER_ID}`（レポートファイル名 `YYYYMMDD_{USER_ID}.md` および `reports/{USER_ID}/` パス構築に使用）
- **メインへの戻り値は「レポート保存完了: ./reports/{USER_ID}/YYYYMMDD_....md」の1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。統合エージェントが直接読み込む。

**注意**:
- `reports/` は `.gitignore` に追加済み
- HISTORY.mdの更新やhistory/スナップショットの作成はこのスキルでは行わない。これらは `/publish-report confirm`（記事確定時）に実行される。記事化しない場合はユーザーが手動で更新を指示する。詳細は `reports/demo/PROMPT.md` の「週次分析フロー」を参照

## エージェント設定・関連ファイル

詳細は `./execution-details.md` の「エージェント設定」「関連ファイル」を参照。全エージェントはTaskツールで起動する（TeamCreateは使用しない）。

## 完了条件

- [ ] WebSearchで市場環境情報を収集し、市場環境サマリーを作成した
- [ ] 全データソース（12種類）を取得・活用した
- [ ] 保有銘柄一覧（数量・単価・評価額・損益・比率）を作成した
- [ ] シャープレシオを全保有銘柄で算出した
- [ ] 相関分析（月次リターンベース）を実施した
- [ ] 最大ドローダウンを実データから算出した
- [ ] VaR/CVaR分析を実施した（月次データ6ヶ月以上の場合）
- [ ] 5軸×6視点のスコア分析を実施した
- [ ] モメンタム（勢いラベル）分析を実施した
- [ ] クロスレビューで矛盾・洞察を発見した（ノーマル・議論重視モードのみ。速度重視モードではスキップ）
- [ ] 合意度100%の推奨アクションを明示した
- [ ] 最適化前後の比較表（指標比較+保有銘柄の改善前後比較）を作成した
- [ ] アクションアイテムを優先度別に整理した
- [ ] レポートファイルが `./reports/{USER_ID}/` ディレクトリに保存された
- [ ] レポート保存後の数値整合性チェック（portfolio_reference.mdとの照合）がパスした
