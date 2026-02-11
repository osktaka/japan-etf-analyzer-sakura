# ポートフォリオ定量分析スキル

```yaml
---
name: portfolio-analysis
description: ポートフォリオ定量分析・最適化（システム全データ活用）
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Task, TaskCreate, TaskUpdate, TaskList, TeamCreate, TeamDelete, SendMessage, WebSearch, WebFetch, AskUserQuestion, Write
aliases: ["/portfolio-analysis", "/pf-analysis"]
---
```

## 概要

このスキルは、ユーザーのETFポートフォリオをシステムが保持する全データを活用して定量分析し、最適化提案を行うワークフロー。エージェントチーム（3名体制）で並行分析→クロスレビュー→統合レポートを作成する。

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
Phase 3: 統合レポート作成（クロスレビューなし）
    ↓
Phase 4: レポート保存
```

- Phase 0aとPhase 0を並行実行（通常は0a→0の順序だが、速度重視では同時開始）
- Phase 2（クロスレビュー）を完全スキップ
- レポートのセクション9「クロスレビューで発見された矛盾と洞察」は「速度重視モードのためスキップ」と記載

#### ノーマル（normal）

```
Phase 0a + Phase 0: 並行実行（市場環境調査とデータ収集を同時実行）
    ↓
Phase 1: タスク分割型並行分析（3エージェントが別々のタスクを担当）
    ↓
Phase 2: クロスレビュー1回（quant↔score相互レビュー）
    ↓
Phase 3: 統合レポート作成
    ↓
Phase 4: レポート保存
```

- Phase 0aの結果はPhase 1で初めて使われるため、Phase 0と並行実行しても問題ない

#### 議論重視（debate）

```
Phase 0a + Phase 0: 市場環境調査 + データ収集
    ↓
Phase 1: 独立分析（2-3エージェントが同じデータを独立に分析）
    ↓
Phase 2a: 第1ラウンド（相互レビュー + 矛盾の指摘）
    ↓
Phase 2b: 第2ラウンド（反論 + 合意形成）
    ↓
Phase 3: 統合レポート作成（議論の経緯を含む）
    ↓
Phase 4: レポート保存
```

- Phase 1では3エージェントが**同じ全データ**を受け取り、それぞれ独立に分析
- Phase 2を2ラウンドに拡張（相互レビュー→反論→合意形成）
- レポートのセクション9に議論の経緯を詳細に記載

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
| おすすめAPI | GET /api/v1/recommend/recommendations?perspective=... | 代替銘柄候補（balance, dividend, low-cost視点） |
| タグ情報 | etf_tag_relations + tags テーブル | セクター/地域/テーマ分類 |
| ETF詳細 | etfs テーブル | 信託報酬、配当利回り、純資産、運用会社、上場日 |
| 入出金記録 | cash_flows テーブル | 現金残高計算 |
| 市場環境調査 | WebSearch + WebFetch | 主要指標・政治経済トピック・分析への示唆 |

## 重要な注意事項

### データ不十分時のスキップ判断

分析項目ごとにデータの充足度を事前に確認し、十分な計算・分析ができない場合は無理に実行せずスキップすること。

**スキップ判断基準**:

| 分析項目 | 必要データ | スキップ条件 |
|---------|-----------|-------------|
| シャープレシオ | 1年リターン、ボラティリティ | performance_cacheに1年データが存在しない銘柄 |
| 相関分析 | 月次価格データ（最低6ヶ月） | 価格履歴が6ヶ月未満、または保有銘柄が1銘柄のみ |
| 最大ドローダウン | 資産推移データ | valuation-historyのデータポイントが10件未満 |
| ストレスシナリオ | ボラティリティ、保有比率 | シャープレシオ算出がスキップされた場合 |
| スコア分析 | score_cache | スコアキャッシュが未生成の銘柄 |
| モメンタム分析 | momentum_label | ラベルがNULLの銘柄 |
| 現金比率 | cash_flows | 入出金記録が0件 |
| クロスレビュー | Phase 1の分析結果 | レビュー対象の分析がスキップされた場合 |

**スキップ時の対応**:
1. レポートの該当セクションに「データ不足のためスキップ」と明記し、不足データの内容を記載する
2. 完了条件のチェックリストでも「データ不足によりスキップ」と注記する
3. スキップした項目数が全体の半数を超える場合は、ユーザーにデータ蓄積を待つことを提案する

### 株式分割の取り扱い

**警告**: DBの生の取引データ（tradesテーブル）は分割前の元の数量・単価で記録されている。正確な損益はPortfolioService（API）経由で取得すること。

- 保有銘柄データは **必ずAPI経由** で取得
- SQLiteに直接クエリすると分割前のデータが返される
- 詳細はCLAUDE.mdの「株式分割の管理」セクションを参照

### APIアクセス方法

Docker環境内からcurl（またはPython requests）でアクセス。認証にはログインしてセッションCookieを使用。

```bash
# Docker環境内からAPIにアクセス
docker compose exec backend python -c "
import requests
session = requests.Session()
session.post('http://localhost:8902/api/v1/auth/login',
  json={'user_id': 'test', 'password': 'testpass123'})
resp = session.get('http://localhost:8902/api/v1/portfolio/holdings')
print(resp.json())
"
```

※テストユーザーの認証情報はCLAUDE.mdの「テストユーザー」セクションを参照。

## 実行フロー

### Phase 0a: 市場環境調査（WebSearch）

レポートの冒頭に掲載する「市場環境サマリー」の情報を収集する。Phase 0のデータ収集前に実施し、分析エージェントへの共有情報として活用。

**速度重視・ノーマルモード**: Phase 0と並行実行する。

詳細な収集手順・まとめ形式は `agent-instructions.md` の「Phase 0a: 市場環境調査」セクションを参照。

### Phase 0: データ収集（Bashエージェントに委譲）

以下のデータを一括取得する。対象銘柄はAPI取得後の保有銘柄リストから動的に決定。

**収集データリスト**:
1. APIからポートフォリオデータ取得（ログイン → holdings → summary）
2. performance_cache（全保有銘柄の8期間リターン・ボラティリティ・回帰率）
3. score_cache（全保有銘柄の5軸×6視点スコア）
4. etfs（momentum_label, manager, listing_date, deviation_rate）
5. 月次価格データ（price_histories、直近13ヶ月の月初価格）
6. 資産推移API（valuation-history?period=3y）
7. タグ情報（etf_tag_relations JOIN tags）
8. おすすめ銘柄API（balance, dividend, low-cost の各視点トップ10）
9. 比較API（保有銘柄同士のperformance, scores）

詳細なスクリプト例は `agent-instructions.md` の「Phase 0: データ収集」セクションを参照。

### Phase 1: 並行分析（エージェントチーム）

TeamCreateでチームを作成し、エージェントを並行起動。各エージェントの詳細な分析項目・計算方法・出力形式は `agent-instructions.md` の「Phase 1: 並行分析」セクションを参照。

#### 速度重視・ノーマルモード: タスク分割型

3エージェントがそれぞれ**異なるタスク**を並行実行（現在の構成と同じ）。

| エージェント | 役割 | 分析項目 |
|-------------|------|---------|
| quant-analyst | 定量リスク・リターン分析 | シャープレシオ、相関分析、最大ドローダウン、ストレスシナリオ、リスク調整後ランキング |
| score-analyst | スコア・モメンタム分析 | 加重平均スコア、モメンタム分析、低スコア銘柄深掘り、代替銘柄提案、運用会社集中リスク、タグベース分散度 |
| allocation-analyst | アセットアロケーション分析 | 地域別配分、セクター別配分、テーマ別配分、欠落アセットクラス、現金比率、集中度ヒートマップ |

**注意**: allocation-analystは、保有銘柄が5銘柄以上の場合に起動。4銘柄以下の場合はquant-analystまたはscore-analystに統合。

#### 議論重視モード: 独立分析型

2-3エージェントが**同じ全データ**を受け取り、それぞれ独立に全項目を分析。
各エージェントは自分なりの優先順位付け・総合判断を行い、最終的に議論で合意を形成する。

| エージェント | 役割 | 分析範囲 |
|-------------|------|---------|
| analyst-A | 独立分析者A | 全項目（リスク、スコア、配分） |
| analyst-B | 独立分析者B | 全項目（リスク、スコア、配分） |
| analyst-C（任意） | 独立分析者C | 全項目（リスク、スコア、配分）※銘柄数が多い場合のみ |

詳細は `agent-instructions.md` の「議論重視モード: 独立分析の指示」セクションを参照。

### Phase 2: クロスレビュー

**速度重視モード**: スキップ。

**ノーマルモード**: Phase 1の結果を各エージェントに送り、相手の分析をレビューさせる（1ラウンド）。
詳細なレビュー観点・出力形式は `agent-instructions.md` の「Phase 2: クロスレビュー」セクションを参照。

**議論重視モード**: 2ラウンド実施。
詳細は `agent-instructions.md` の「Phase 2: クロスレビュー（議論重視モード）」セクションを参照。

### Phase 3: 統合レポート作成

全分析結果とクロスレビューのフィードバックを統合し、最終レポートを作成。

レポートの出力形式テンプレートは `report-template.md` を参照。

### Phase 4: レポート保存

統合レポートをマークダウンファイルとしてプロジェクトルートの `./reports/` ディレクトリに保存する。

**手順**:

1. `./reports/` ディレクトリが存在しない場合は作成
   ```bash
   mkdir -p ./reports
   ```
2. レポート内容をマークダウンファイルとして保存
   - ファイル名形式: `YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
   - username未指定時: `YYYYMMDD_HHMMSS_portfolio_analysis.md`
   - 例: `20260211_143025_portfolio_analysis_test.md`
3. 保存先パスをユーザーに通知
   ```
   レポートを保存しました: ./reports/20260211_143025_portfolio_analysis_test.md
   ```

**注意**: `reports/` は `.gitignore` に追加済み（レポートファイルはGit管理対象外）。未追加の場合は以下で追加:
```bash
grep -q '^reports/' .gitignore || echo 'reports/' >> .gitignore
```

**注意**: レポート保存はPhase 3の統合レポート作成が完了した後に実施する。保存に失敗した場合でも、レポート自体はチャット上で表示されるため、分析結果が失われることはない。

## エージェント設定

### 速度重視・ノーマルモード

| エージェント | subagent_type | model | 役割 |
|-------------|---------------|-------|------|
| quant-analyst | general-purpose | sonnet | 定量リスク・リターン分析 |
| score-analyst | general-purpose | sonnet | スコア・モメンタム分析 |
| allocation-analyst | general-purpose | sonnet | アセットアロケーション分析（必要時） |
| データ収集 | Bash | - | API/DB一括データ取得 |

### 議論重視モード

| エージェント | subagent_type | model | 役割 |
|-------------|---------------|-------|------|
| analyst-A | general-purpose | sonnet | 独立分析者A（全項目分析） |
| analyst-B | general-purpose | sonnet | 独立分析者B（全項目分析） |
| analyst-C | general-purpose | sonnet | 独立分析者C（銘柄数が多い場合のみ） |
| データ収集 | Bash | - | API/DB一括データ取得 |

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `agent-instructions.md` | Phase 0a/0/1/2の詳細指示（サブエージェントへ渡す情報） |
| `report-template.md` | Phase 3統合レポートの出力形式テンプレート |
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
- [ ] 5軸×6視点のスコア分析を実施した
- [ ] モメンタム（勢いラベル）分析を実施した
- [ ] クロスレビューで矛盾・洞察を発見した（ノーマル・議論重視モードのみ。速度重視モードではスキップ）
- [ ] 合意度100%の推奨アクションを明示した
- [ ] 最適化前後の比較表（指標比較+保有銘柄の改善前後比較）を作成した
- [ ] アクションアイテムを優先度別に整理した
- [ ] レポートファイルが `./reports/` ディレクトリに保存された
