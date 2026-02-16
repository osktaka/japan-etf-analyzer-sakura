# 実行詳細リファレンス

SKILL.md から分離した実行詳細情報。メインエージェントが必要時に参照する。

## ファイル構成

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
├── YYYYMMDD_{username}.md  # レポート本体（全ユーザー共通、reports/直下）
└── demo/
    ├── PROMPT.md                # 週次分析プロジェクト定義
    ├── HISTORY.md               # 最新の分析履歴（更新される）
    └── history/
        ├── 20260212.md          # 2/12時点のスナップショット（不変）
        ├── 20260213.md          # 2/13時点のスナップショット（不変）
        └── ...
```

## フェーズレベルの失敗時フォールバックポリシー

個別データのスキップ判断（`data-skip-rules.md` 参照）とは別に、フェーズ全体が失敗した場合の対応を以下に定義する。

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

## 実行時間計測

各フェーズの完了時刻を `{WORK_DIR}/timing.json` に記録する。

**メインエージェントの記録** (2回のBash):
1. WORK_DIR作成時: `{"skill_start": "..."}` で初期化
2. Phase 1完了後: 中間ファイルの更新時刻（`stat`）から `phase_0a_end`, `phase_0_end`, `phase_05_end`（debate時）, `phase_1_end` を一括書き込み

**Phase 3+4の記録**:
- debateモード: オーケストレーターが `phase_3_round1_end`, `phase_3_round2_end`, `phase_4_end`, `skill_end` をファイル更新時刻から記録
- speed/normalモード: 統合エージェントが `phase_3_start`, `phase_3_end`, `skill_end` を記録（従来通り）

**注意**: `_start` イベントはファイル更新時刻から推定できないため記録しない。精度はレポートの実行時間セクションとして十分。

## Phase 3: クロスレビュー詳細（debateモード限定）

**debateモードではPhase 3+4オーケストレーターに委譲**。詳細は `agent-instructions/phase34-debate-orchestrator.md` を参照。

オーケストレーターが内部で以下を実行:
- Round 1: 3エージェント並列起動（相互レビュー）
- Round 2: 3エージェント並列起動（反論・合意形成）
- Phase 4: 統合エージェント起動
- timing.json の Phase 3/4 イベント記録

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
| Phase 3+4 (debate) | オーケストレーター | general-purpose | sonnet | 20分 | `agent-instructions/phase34-debate-orchestrator.md` |
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
| `report-guide.md` | レポートガイド（テンプレート＋書き方） |
| `agent-instructions/crossreview-normal.md` | ノーマル クロスレビュー観点 |
| `agent-instructions/crossreview-debate.md` | debate クロスレビュー観点 |
| CLAUDE.md「株式分割の管理」セクション | 分割調整の仕組み |
| CLAUDE.md「テストユーザー」セクション | 認証情報 |
| docs/08_おすすめ銘柄設計.md | 5軸評価・6視点の詳細 |
| docs/09_タグ付けルール.md | 6カテゴリ49タグの定義 |
| backend/src/services/portfolio_service.py | 分割調整済みポートフォリオ計算 |
| backend/src/services/split_adjustment_service.py | 株式分割調整ロジック |
