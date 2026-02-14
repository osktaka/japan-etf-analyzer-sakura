# Phase 3+4: 統合レポート作成・保存 指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`

## データ受け渡しルール

- **入力**: `{WORK_DIR}/` 配下の全分析結果ファイル、`{skill_dir}/report-template.md`
- **出力**: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
- **メインへの戻り値**: 「レポート保存完了: ./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md」の1行のみ。データ全文やテーブル全体を返さないこと

---

## 統合エージェントの役割

統合エージェント（general-purpose）は、`{WORK_DIR}` 配下の全分析結果ファイルを読み込み、`report-template.md` のテンプレートに従ってレポートを作成・保存する。

## 入力ファイル

### 共通（全モード）

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/market_environment.md` | 市場環境サマリー |
| `{WORK_DIR}/portfolio_data.json` | 全収集データ |
| `{WORK_DIR}/timing.json` | 各フェーズの実行時間記録 |
| `{skill_dir}/report-template.md` | レポート出力形式テンプレート |

### speed/normalモード

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/quant_analysis.md` | 定量リスク・リターン分析結果 |
| `{WORK_DIR}/score_analysis.md` | スコア・モメンタム分析結果 |
| `{WORK_DIR}/allocation_analysis.md` | アセットアロケーション分析結果（存在する場合） |

### debateモード

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/analyst_a_analysis.md` | analyst-A分析結果 |
| `{WORK_DIR}/analyst_b_analysis.md` | analyst-B分析結果 |
| `{WORK_DIR}/analyst_c_analysis.md` | analyst-C分析結果（存在する場合） |

---

## クロスレビュー（統合エージェント内で実施）

モードに応じて、以下のクロスレビュー観点ファイルを読み込み、レポートのセクション9に記載する。

### speedモード

クロスレビューなし。セクション9に「速度重視モードのためスキップ」と記載。

### normalモード

以下のファイルを読み込み、記載された観点で分析結果間の矛盾・整合性を検証する:

- **参照ファイル**: `{skill_dir}/agent-instructions/phase2-crossreview-normal.md`

検証項目（詳細は上記ファイルを参照）:

1. **スコアとシャープレシオの乖離**: スコア高/シャープ低、またはその逆のケースを特定し、解釈を記載
2. **代替銘柄提案の定量的妥当性**: 提案銘柄のシャープレシオ・相関係数を確認
3. **失速銘柄のリスク整合性**: モメンタムとボラティリティの整合性を確認
4. **相関分析とタグ分類の整合性**: 高相関ペアが同一地域/セクターか確認
5. **スコア上の見落としリスク**: シャープは高いが信託報酬が高い、純資産が小さい等

### debateモード

以下のファイルを読み込み、記載された手順で2ラウンドのクロスレビューを実施する:

- **参照ファイル**: `{skill_dir}/agent-instructions/phase2-crossreview-debate.md`

セクション9には議論の経緯を詳細に記載:
- 見解の相違点とその根拠
- 合意された点
- 各アクションの合意度（100%/過半数/不合意）

---

## 出力

1. レポートファイル: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`（**全ユーザー共通で`reports/`直下に保存**）
2. **メインへの戻り値**: 「レポート保存完了: ./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md」の1行のみ

---

## レポート作成手順

1. `{WORK_DIR}/` 配下の全ファイルを読み込む
2. `{skill_dir}/report-template.md` を読み込む
2a. `portfolio_data.json` の `_metadata._data_status` を読み込み、各データソースの取得状態を確認する。Phase 1各アナリストの出力ファイルに記載されたスキップ理由と突合し、「データ活用状況」テーブルを以下のルールで生成する:
    - `_data_status.{source}.status == "ok"` かつ Phase 1で活用された → ✓
    - `_data_status.{source}.status == "ok"` だがPhase 1でデータ不足（条件未充足）によりスキップ → △
    - `_data_status.{source}.status == "empty"` → △（備考: 「空レスポンス」）
    - `_data_status.{source}.status == "error"` → ✗（備考: エラー詳細を転記）
    - Phase 0で取得対象外（条件に該当せず） → -
3. テンプレートに従い、各セクションを実データで埋める
4. クロスレビュー（該当モードの場合）を実施し、セクション9に記載
5. `{WORK_DIR}/timing.json` を読み込み、Phase 3+4の開始時刻（phase_3_start）と完了時刻（phase_3_end, skill_end）を自身で記録した上で、所要時間を計算し「実行時間」セクション（セクション14）に記載する
6. `./reports/` ディレクトリを作成（存在しない場合）
7. **レポート本体を保存**: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
8. メインに保存先パスのみ返す

**注意**: HISTORY.mdの更新やhistory/スナップショットの作成はこのスキルでは行わない。これらは `/publish-report confirm`（記事確定時）に実行される。記事化しない場合はユーザーが手動で更新を指示する。詳細は `reports/demo/PROMPT.md` の「週次分析フロー」を参照

---

## 実行時間の計算方法

- 各フェーズの所要時間 = end - start（秒単位で計算し、X分XX秒で表示）
- Phase 0a+0 合計 = max(phase_0a_end, phase_0_end) - min(phase_0a_start, phase_0_start)（並行実行のため）
- 合計 = skill_end - skill_start
- phase_3_start: timing.jsonを読み込んだ直後に現在時刻を記録
- phase_3_end / skill_end: レポート保存直前に現在時刻を記録
