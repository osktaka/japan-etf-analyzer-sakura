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

### メインエージェントの制約

- `agent-instructions/` 配下のファイルは**メインエージェントが読み込まない**
- メインはサブエージェントのプロンプトに**指示ファイルパスとWORK_DIR**を渡すだけ
- サブエージェントが自分の指示ファイルを直接読み込んで実行する

### ファイル構成

```
{WORK_DIR}/
├── market_environment.md    # Phase 0a出力
├── portfolio_data.json      # Phase 0出力
├── portfolio_reference.md   # Phase 0出力（セクション1・11.2用テーブル）
├── shared_calculations.md   # Phase 0.5出力（debateモード限定、共通定量計算結果）
├── quant_analysis.md        # Phase 1: quant-analyst出力
├── score_analysis.md        # Phase 1: score-analyst出力
├── allocation_analysis.md   # Phase 1: allocation-analyst出力
├── crossreview_round1_a.md # Phase 3出力（debateモード限定、analyst-A Round 1レビュー）
├── crossreview_round1_b.md # Phase 3出力（debateモード限定、analyst-B Round 1レビュー）
├── crossreview_round1_c.md # Phase 3出力（debateモード限定、analyst-C Round 1レビュー）
├── crossreview_round2_a.md # Phase 3出力（debateモード限定、analyst-A Round 2反論・合意）
├── crossreview_round2_b.md # Phase 3出力（debateモード限定、analyst-B Round 2反論・合意）
├── crossreview_round2_c.md # Phase 3出力（debateモード限定、analyst-C Round 2反論・合意）
└── timing.json              # 各フェーズの実行時間

reports/
├── YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md  # レポート本体（全ユーザー共通、reports/直下）
└── demo/
    ├── PROMPT.md                # 週次分析プロジェクト定義
    ├── HISTORY.md               # 最新の分析履歴（更新される）
    └── history/
        ├── 20260212.md          # 2/12時点のスナップショット（不変）
        ├── 20260213.md          # 2/13時点のスナップショット（不変）
        └── ...
```

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

```
Phase 0a + Phase 0: 並行実行（市場環境調査とデータ収集を同時実行）
    ↓
Phase 1: タスク分割型並行分析（3エージェントが別々のタスクを担当、重複なし）
    ↓
Phase 3+4: 統合レポート作成・保存（クロスレビューなし）
```

- Phase 0aとPhase 0を並行実行
- クロスレビューを完全スキップ
- レポートのセクション9「クロスレビューで発見された矛盾と洞察」は「速度重視モードのためスキップ」と記載

#### ノーマル（normal）

```
Phase 0a + Phase 0: 並行実行（市場環境調査とデータ収集を同時実行）
    ↓
Phase 1: タスク分割型並行分析（3エージェントが別々のタスクを担当）
    ↓
Phase 3+4: 統合レポート作成・保存（クロスレビュー含む）
```

- Phase 0aの結果はPhase 1で初めて使われるため、Phase 0と並行実行しても問題ない
- クロスレビューは統合エージェント内で実施（独立フェーズではない）

#### 議論重視（debate）

```
Phase 0a + Phase 0: 市場環境調査 + データ収集
    ↓
Phase 0.5: 共通定量計算（debateモード限定）
    ↓
Phase 1: ペルソナ別解釈・判断（3エージェントが同じデータ+共通計算結果を独立に分析）
    ↓
Phase 3: クロスレビュー2ラウンド（3エージェント並列 x 2ラウンド、メインがオーケストレーション）
    ↓
Phase 4: 統合レポート作成・保存（クロスレビュー結果を読み込み統合）
```

- Phase 0完了後、Phase 0.5で共通定量計算を1エージェント（general-purpose, sonnet）で実行し、決定論的な計算結果（シャープレシオ、相関係数、ドローダウン等）を `shared_calculations.md` に出力する
- Phase 1では3エージェントが**同じ全データ+共通計算結果**を受け取り、計算の再実行なしにペルソナごとの解釈・見解・提言を独立に行う
- Phase 0.5はdebateモード限定。normalモード/speedモードには影響しない
- クロスレビュー（2ラウンド: 相互レビュー→反論→合意形成）はPhase 3で独立エージェントが実施し、Phase 4の統合エージェントが結果を読み込み統合する
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

個別データのスキップ判断（下記セクション参照）とは別に、フェーズ全体が失敗した場合の対応を以下に定義する。

| フェーズ | 失敗条件 | 対応 |
|---------|---------|------|
| Phase 0a | WebSearch/WebFetch全て失敗 | market_environment.md なしで続行。Phase 1は市場環境言及をスキップ。レポートのセクション0に「市場環境調査失敗」と記載 |
| Phase 0 | API認証失敗、またはholdings取得失敗 | **スキル全体を中止**。ユーザーにエラー内容を報告 |
| Phase 0 | holdings成功だがDB系データが全て失敗 | portfolio_data.json をAPI取得分のみで保存して続行。Phase 1は `_data_status` に基づき個別にスキップ |
| Phase 0.5 (debate) | スクリプト実行失敗 | Phase 1のペルソナエージェントが各自で計算を実行（shared_calculations.md が存在しなければ自力計算にフォールバック） |
| Phase 1 | 3体中1体が失敗 | 残り2体の結果で続行。レポートの該当セクションに「分析失敗のため省略」と記載 |
| Phase 1 | 3体中2体以上が失敗 | **スキル全体を中止**。ユーザーにエラー内容を報告 |
| Phase 3 (debate) | 3体中1体が失敗 | 残り2体のレビュー結果で続行。セクション9の該当ペルソナの議論を「レビュー失敗のため省略」と記載 |
| Phase 3 (debate) | 3体中2体以上が失敗 | Phase 3をスキップし、Phase 4の統合エージェント内でクロスレビューをシミュレート（従来方式にフォールバック）。セクション9に「独立クロスレビュー失敗のためシミュレート実施」と記載 |
| Phase 4 | レポート作成失敗 | メインエージェントがユーザーにエラー報告。WORK_DIR内の中間ファイルパスを提示し、手動確認を促す |

**メインエージェントの判断フロー**:
1. 各フェーズのサブエージェント完了後、出力ファイルの存在を確認
2. 上記テーブルに従い、続行/中止を判断
3. 中止する場合、ユーザーにエラー内容と推奨アクション（「Docker環境を確認する」「APIサーバーの起動状態を確認する」等）を報告

### データ不十分時のスキップ判断

分析項目ごとにデータの充足度を事前に確認し、十分な計算・分析ができない場合は無理に実行せずスキップすること。

> **注記**: 各分析項目の詳細なスキップ条件は、各エージェント指示書（`agent-instructions/phase1-*.md`）が正（single source of truth）。以下のテーブルはメインエージェントの完了確認用サマリーである。

**スキップ判断基準**:

| 分析項目 | スキップ条件 |
|---------|-------------|
| シャープレシオ | `_data_status.performance_cache`がerror/empty、またはperiodsに1yが含まれない |
| 相関分析 | `_data_status.price_data`がerror/empty、価格履歴が6ヶ月未満、または保有銘柄が1銘柄のみ |
| 最大ドローダウン | `_data_status.valuation_history`がerror/empty、またはデータポイントが10件未満 |
| ストレスシナリオ | シャープレシオ算出がスキップされた場合 |
| VaR/CVaR | 月次リターンデータが6ヶ月未満の場合スキップ。6-11ヶ月は参考値として算出 |
| スコア分析 | `_data_status.score_cache`がerror/empty、またはスコアキャッシュが未生成の銘柄 |
| モメンタム分析 | `_data_status.etf_data`がerror/empty、またはラベルが全銘柄NULL |
| 現金比率 | `_data_status.summary`がerror/empty、またはsummaryにcash_balanceが含まれない |
| クロスレビュー | レビュー対象の分析がスキップされた場合 |

**スキップ時の対応**:
1. レポートの該当セクションにスキップ理由を以下の3分類で明記する:
   - 「取得失敗（API/DBエラー）」: `_data_status`のstatusが"error"の場合。エラー詳細も記載する
   - 「データ不足（空レスポンス）」: `_data_status`のstatusが"empty"の場合
   - 「データ不足（条件未充足）」: データは存在するが分析条件を満たさない場合（例: performance_cacheはあるが1yデータがない）
2. 完了条件のチェックリストでも上記3分類でスキップ理由を注記する
3. スキップした項目数が全体の半数を超える場合は、ユーザーにデータ蓄積を待つことを提案する

### スキップ前の原因調査（必須）

「データ不足」でスキップする前に、以下の調査を行うこと:

1. **`_metadata`セクションの確認**: portfolio_data.jsonの`_metadata`で該当データの件数・カラム名を確認
2. **フィールド名の照合**: スクリプトで使用しているフィールド名が`_metadata`の記載と一致するか確認
3. **不一致時の自己修正**: フィールド名が異なる場合、`_metadata`の正しい名前で修正して再実行
4. **真のデータ不足のみスキップ**: `_metadata`の件数が0、またはNULL/空配列の場合のみスキップ可

**禁止事項**: `_metadata`を確認せずに「データ不足」と判断すること

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

各フェーズの開始・終了時刻をメインエージェントが記録し、`{WORK_DIR}/timing.json` に保存する。統合エージェントがこのファイルを読み込み、レポート末尾に実行時間セクションを出力する。

**記録タイミング**:

| イベント | 記録タイミング |
|---------|--------------|
| skill_start | スキル実行開始時（WORK_DIR作成直後） |
| phase_0a_start | Phase 0aサブエージェント起動直前 |
| phase_0_start | Phase 0サブエージェント起動直前 |
| phase_0a_end | Phase 0aサブエージェント完了時 |
| phase_0_end | Phase 0サブエージェント完了時 |
| phase_05_start | Phase 0.5サブエージェント起動直前（debateモード時のみ） |
| phase_05_end | Phase 0.5サブエージェント完了時（debateモード時のみ） |
| phase_1_start | Phase 1サブエージェント起動直前 |
| phase_1_end | Phase 1全サブエージェント完了時 |
| phase_3_round1_start | Phase 3 Round 1エージェント起動直前（debateモード時） |
| phase_3_round1_end | Phase 3 Round 1全エージェント完了時（debateモード時） |
| phase_3_round2_start | Phase 3 Round 2エージェント起動直前（debateモード時） |
| phase_3_round2_end | Phase 3 Round 2全エージェント完了時（debateモード時） |
| phase_4_start | Phase 4統合エージェント起動直前 |
| phase_4_end | Phase 4統合エージェント完了時 |
| phase_3_start | Phase 3+4統合エージェント起動直前（speed/normalモード時。後方互換のため名称維持） |
| phase_3_end | Phase 3+4統合エージェント完了時（speed/normalモード時。後方互換のため名称維持） |
| skill_end | スキル完了時 |

**記録方法**: Bashツールでタイムスタンプを追記する。

初期作成（skill_start時）:
```bash
echo '{}' > {WORK_DIR}/timing.json
python3 -c "
import json, datetime
data = {'skill_start': datetime.datetime.now().isoformat()}
with open('{WORK_DIR}/timing.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

各フェーズの記録:
```bash
python3 -c "
import json, datetime
with open('{WORK_DIR}/timing.json') as f:
    data = json.load(f)
data['phase_0a_start'] = datetime.datetime.now().isoformat()
with open('{WORK_DIR}/timing.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

**注意**: timing.json の保存は Phase 3+4 起動前に完了させること（phase_3_start と skill_end は統合エージェント内で記録）。

### Phase 0a: 市場環境調査（general-purposeエージェントに委譲）

レポートの冒頭に掲載する「市場環境サマリー」の情報を収集する。**general-purposeサブエージェント**に委譲し、Phase 0と並行実行する。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase0a-market-research.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- **メインへの戻り値は「市場環境調査完了」の1行のみ**

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
10. `portfolio_reference.md`の生成（セクション1・11.2用のmarkdownテーブルをPythonで自動生成）

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

### Phase 3: クロスレビュー（debateモード限定）

**実行条件**: debateモードのみ。speed/normalモードでは実行しない。
**開始条件**: Phase 1の3エージェント全員が完了してから起動する。

メインエージェントが multi-persona パターン（Task + run_in_background + TaskOutput）で2ラウンドのクロスレビューをオーケストレーションする。

#### Round 1: 相互レビュー

3エージェントを**同一ターンで並列起動**（run_in_background: true）。各エージェントは他2名の分析結果を読み込み、自身のペルソナの視点でレビューを行う。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/crossreview-debate-agent.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- ペルソナ: `{persona}`（analyst-A / analyst-B / analyst-C）
- ラウンド: `1`
- skill_dir: `{skill_dir}`
- **メインへの戻り値は「{ペルソナ名} Round 1 レビュー完了」の1行のみ**

メインエージェントは `TaskOutput` で3エージェントの完了を待機。

#### Round 2: 反論・合意形成

Round 1の全レビュー結果ファイルが出揃った後、3エージェントを再度**同一ターンで並列起動**（run_in_background: true）。各エージェントは自分へのレビュー結果を読み込み、反論・合意を表明する。

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/crossreview-debate-agent.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- ペルソナ: `{persona}`（analyst-A / analyst-B / analyst-C）
- ラウンド: `2`
- skill_dir: `{skill_dir}`
- **メインへの戻り値は「{ペルソナ名} Round 2 合意形成完了」の1行のみ**

メインエージェントは `TaskOutput` で3エージェントの完了を待機。

### Phase 4: 統合レポート作成・保存（統合エージェントに委譲）

レポートの作成・保存はメインエージェントが行わず、**統合エージェント（general-purpose）**に委譲する。

- **speed/normalモード**: Phase 1の分析結果を統合し、クロスレビュー（normalの場合）も統合エージェント内で実施
- **debateモード**: Phase 1の分析結果 + Phase 3のクロスレビュー結果を読み込み、レポートに統合（クロスレビュー自体はPhase 3で完了済み）

**サブエージェントへの指示**: プロンプトに以下を含める:
- 指示ファイル: `{skill_dir}/agent-instructions/phase34-integration.md` を読んで実行
- WORK_DIR: `{WORK_DIR}`
- モード: `{mode}`（speed/normal/debate）
- skill_dir: `{skill_dir}`
- **メインへの戻り値は「レポート保存完了: ./reports/YYYYMMDD_....md」の1行のみ**

**メインエージェントは指示ファイルの内容を読み込まない**。統合エージェントが直接読み込む。

**注意**:
- `reports/` は `.gitignore` に追加済み
- HISTORY.mdの更新やhistory/スナップショットの作成はこのスキルでは行わない。これらは `/publish-report confirm`（記事確定時）に実行される。記事化しない場合はユーザーが手動で更新を指示する。詳細は `reports/demo/PROMPT.md` の「週次分析フロー」を参照

## エージェント設定

全エージェントはTaskツールで起動する（TeamCreateは使用しない）。

| フェーズ | エージェント | subagent_type | model | タイムアウト | 指示ファイル |
|---------|------------|---------------|-------|------------|------------|
| Phase 0a | 市場環境調査 | general-purpose | sonnet | 3分 | `agent-instructions/phase0a-market-research.md` |
| Phase 0 | データ収集 | Bash | - | 2分 | `agent-instructions/phase0-data-collection.md` |
| Phase 0.5 (debate) | 共通定量計算 | general-purpose | sonnet | 3分 | `agent-instructions/phase05-shared-calculations.md` |
| Phase 1 (speed/normal) | quant-analyst | general-purpose | sonnet | 5分 | `agent-instructions/phase1-quant-analyst.md` |
| Phase 1 (speed/normal) | score-analyst | general-purpose | sonnet | 5分 | `agent-instructions/phase1-score-analyst.md` |
| Phase 1 (speed/normal) | allocation-analyst | general-purpose | sonnet | 5分 | `agent-instructions/phase1-allocation-analyst.md` |
| Phase 1 (debate) | analyst-A/B/C | general-purpose | sonnet | 8分 | `agent-instructions/phase1-debate-common.md` + quant/score/allocation |
| Phase 3 (debate) Round 1 | analyst-A/B/C レビュー | general-purpose | sonnet | 5分 | `agent-instructions/crossreview-debate-agent.md` |
| Phase 3 (debate) Round 2 | analyst-A/B/C 反論・合意 | general-purpose | sonnet | 5分 | `agent-instructions/crossreview-debate-agent.md` |
| Phase 4 | 統合レポート | general-purpose | sonnet | 10分 | `agent-instructions/phase34-integration.md` |

### タイムアウト補足

- 上記タイムアウトはサブエージェント起動時の目安。超過時はフォールバックポリシーの「失敗」として扱う
- Phase 0のHTTP通信設定（phase0-collection-template.py参照）:
  - リクエストタイムアウト: 30秒/リクエスト
  - リトライ上限: 3回（指数バックオフ: 1秒→2秒→4秒）
  - 認証リクエスト: リトライなし（即座に失敗）

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `report-template.md` | レポート出力テンプレート |
| `report-writing-guide.md` | レポート書き方ガイド（補足・議論重視ルール） |
| `agent-instructions/crossreview-normal.md` | ノーマル クロスレビュー観点 |
| `agent-instructions/crossreview-debate.md` | debate クロスレビュー観点 |
| CLAUDE.md「株式分割の管理」セクション | 分割調整の仕組み |
| CLAUDE.md「テストユーザー」セクション | 認証情報 |
| docs/08_おすすめ銘柄設計.md | 5軸評価・6視点の詳細 |
| docs/09_タグ付けルール.md | 6カテゴリ49タグの定義 |
| backend/src/services/portfolio_service.py | 分割調整済みポートフォリオ計算 |
| backend/src/services/split_adjustment_service.py | 株式分割調整ロジック |

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
- [ ] レポートファイルが `./reports/` ディレクトリに保存された
- [ ] レポート保存後の数値整合性チェック（portfolio_reference.mdとの照合）がパスした
