# Phase 3+4 オーケストレーター（debateモード専用）

メインエージェントから委譲され、Phase 3（クロスレビュー2ラウンド）+ Phase 4（統合レポート）を一括オーケストレーションする。

## 受け取るパラメータ

- `WORK_DIR`: 作業ディレクトリパス
- `skill_dir`: スキルディレクトリパス（`.claude/skills/portfolio-analysis`）
- `mode`: 常に `debate`

## 実行フロー

### Step 1: Phase 3 Round 1（相互レビュー）

5エージェントを **同一ターンで並列起動**（run_in_background: true）。各エージェントはサイクル上の隣接2名の分析結果を読み込み、自身のペルソナの視点でレビューを行う。

timing.json に `phase_3_round1_start` を記録してから起動する。

**注意**: Phase 2はメインエージェントが起動済みであり、`{WORK_DIR}/20_candidate_verification.md` が存在する場合はPhase 3のクロスレビューエージェントに渡すこと。

**Taskツールで起動（5回、同一ターン）**:
- subagent_type: general-purpose
- model: sonnet
- プロンプトに含めるパラメータ:
  - 指示ファイル: `{skill_dir}/agent-instructions/crossreview-debate-agent.md` を読んで実行
  - WORK_DIR: `{WORK_DIR}`
  - ペルソナ: 各エージェントに1つずつ
    - `analyst-A`（積極派）: レビュー対象はB（堅実派）とE（長期構造派）
    - `analyst-B`（堅実派）: レビュー対象はA（積極派）とC（異論派）
    - `analyst-C`（異論派）: レビュー対象はB（堅実派）とD（マクロ戦略派）
    - `analyst-D`（マクロ戦略派）: レビュー対象はC（異論派）とE（長期構造派）
    - `analyst-E`（長期構造派）: レビュー対象はD（マクロ戦略派）とA（積極派）
  - ラウンド: `1`
  - skill_dir: `{skill_dir}`
  - 入力ファイル: `{WORK_DIR}/20_candidate_verification.md`（存在する場合のみ）
  - **メインへの戻り値は「{ペルソナ名} Round 1 レビュー完了」の1行のみ**

TaskOutput(blocking) で5体の完了を待機する。

**完了確認**: 以下5ファイルの存在を確認する。
- `{WORK_DIR}/31_crossreview_a.md`
- `{WORK_DIR}/31_crossreview_b.md`
- `{WORK_DIR}/31_crossreview_c.md`
- `{WORK_DIR}/31_crossreview_d.md`
- `{WORK_DIR}/31_crossreview_e.md`

timing.json に `phase_3_round1_end` を記録する。

### Step 2: Phase 3 Round 2（反論・合意形成）

Round 1の全レビュー結果ファイルが出揃った後、5エージェントを再度 **同一ターンで並列起動**（run_in_background: true）。各エージェントは自分へのレビュー結果（サイクル上の隣接2名からのRound 1出力）を読み込み、反論・合意を表明する。

timing.json に `phase_3_round2_start` を記録してから起動する。

**Taskツールで起動（5回、同一ターン）**:
- subagent_type: general-purpose
- model: sonnet
- プロンプトに含めるパラメータ:
  - 指示ファイル: `{skill_dir}/agent-instructions/crossreview-debate-agent.md` を読んで実行
  - WORK_DIR: `{WORK_DIR}`
  - ペルソナ: 各エージェントに1つずつ（Round 2指定）
    - `analyst-A`: 読み込むレビューファイルは `31_crossreview_b.md`（BからR1）+ `31_crossreview_e.md`（EからR1）
    - `analyst-B`: 読み込むレビューファイルは `31_crossreview_a.md`（AからR1）+ `31_crossreview_c.md`（CからR1）
    - `analyst-C`: 読み込むレビューファイルは `31_crossreview_b.md`（BからR1）+ `31_crossreview_d.md`（DからR1）
    - `analyst-D`: 読み込むレビューファイルは `31_crossreview_c.md`（CからR1）+ `31_crossreview_e.md`（EからR1）
    - `analyst-E`: 読み込むレビューファイルは `31_crossreview_d.md`（DからR1）+ `31_crossreview_a.md`（AからR1）
  - ラウンド: `2`
  - skill_dir: `{skill_dir}`
  - **メインへの戻り値は「{ペルソナ名} Round 2 合意形成完了」の1行のみ**

TaskOutput(blocking) で5体の完了を待機する。

**完了確認**: 以下5ファイルの存在を確認する。
- `{WORK_DIR}/32_crossreview_a.md`
- `{WORK_DIR}/32_crossreview_b.md`
- `{WORK_DIR}/32_crossreview_c.md`
- `{WORK_DIR}/32_crossreview_d.md`
- `{WORK_DIR}/32_crossreview_e.md`

timing.json に `phase_3_round2_end` を記録する。

### Step 3: Phase 4 統合レポート

timing.json に `phase_4_start` を記録してから起動する。

**Taskツールで起動（1回）**:
- subagent_type: general-purpose
- model: sonnet
- プロンプトに含めるパラメータ:
  - 指示ファイル: `{skill_dir}/agent-instructions/phase34-integration.md` を読んで実行
  - WORK_DIR: `{WORK_DIR}`
  - モード: `debate`
  - skill_dir: `{skill_dir}`
  - 入力ファイル（抜粋読込ルールを適用すること）:
    - 分析5ファイル（`10_analyst_{a,b,c,d,e}_analysis.md`）: 総合判断セクションのみ抜粋
    - クロスレビュー10ファイル（`31_crossreview_{a,b,c,d,e}.md`, `32_crossreview_{a,b,c,d,e}.md`）: 合意/反論結果のみ抜粋
    - `{WORK_DIR}/20_candidate_verification.md`（存在する場合のみ）
    - `{WORK_DIR}/00_portfolio_data.json`（`compare_performance`, `compare_scores`のみ参照）
    - `{WORK_DIR}/05_shared_calculations.md`
  - **メインへの戻り値は「レポート保存完了: ./reports/{username}/YYYYMMDD_....md」の1行のみ**

TaskOutput(blocking) で完了を待機し、戻り値からレポートパスを取得する。

timing.json に `phase_4_end` と `skill_end` を記録する。

### Step 4: timing.json 最終確認

各イベントは Step 1-3 内で記録済み。timing.json を読み込み、以下の全イベントが存在するか確認する:

`phase_3_round1_start`, `phase_3_round1_end`, `phase_3_round2_start`, `phase_3_round2_end`, `phase_4_start`, `phase_4_end`, `skill_end`

各Stepの前後で Bashツールを使い、`datetime.now().isoformat()` を timing.json に書き込む（ファイル更新時刻ではなく直接タイムスタンプ）。

## フォールバック

### Task再帰が失敗した場合（Phase 3）

このオーケストレーターからのTask起動が失敗した場合:
- オーケストレーター自身が `10_analyst_a_analysis.md`, `10_analyst_b_analysis.md`, `10_analyst_c_analysis.md`, `10_analyst_d_analysis.md`, `10_analyst_e_analysis.md` を読み込み、直接クロスレビューを実施して `31_crossreview_*.md`, `32_crossreview_*.md` を生成する
- Phase 4 は統合エージェントのみTask起動（1段のTask再帰に縮退）

### Phase 3 で5体中3体以上が失敗した場合

execution-details.md のフォールバックポリシーに従う:
- Phase 3をスキップし、Phase 4の統合エージェント内でクロスレビューをシミュレート（従来方式にフォールバック）
- セクション9に「独立クロスレビュー失敗のためシミュレート実施」と記載

### Phase 3 で5体中1-2体が失敗した場合

- 残りのエージェントのレビュー結果で続行
- セクション9の該当ペルソナの議論を「レビュー失敗のため省略」と記載

## コンテキスト管理ルール

- **メインへの戻り値**: 「Phase 3+4完了: ./reports/{username}/YYYYMMDD_....md」の1行のみ返す
- 中間データは WORK_DIR 内のファイルに保存。メインへの戻り値にデータ全文を含めない
- TaskOutput は **blocking モードのみ** 使用（non-blocking 禁止）
- 指示ファイル（crossreview-debate-agent.md, phase34-integration.md）の内容はサブエージェントが直接読み込む。このファイルでは内容を重複記載しない
