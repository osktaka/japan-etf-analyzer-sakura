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
3. テンプレートに従い、各セクションを実データで埋める
4. クロスレビュー（該当モードの場合）を実施し、セクション9に記載
5. `{WORK_DIR}/timing.json` を読み込み、Phase 3+4の開始時刻（phase_3_start）と完了時刻（phase_3_end, skill_end）を自身で記録した上で、所要時間を計算し「実行時間」セクション（セクション14）に記載する
6. `./reports/` ディレクトリを作成（存在しない場合）
7. **レポート本体を保存**: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`（**注意**: demoユーザーであっても`reports/demo/`配下には保存しない。`reports/demo/`はHISTORY.mdとスナップショットのみ）
8. **demoユーザーの場合のみ**: HISTORY.md を以下の手順で更新する（レポート保存とは別の手順）
   a. `reports/demo/history/` ディレクトリを作成（存在しない場合）
   b. 当日のスナップショットファイル `reports/demo/history/YYYYMMDD.md` が存在しない場合、現在の `reports/demo/HISTORY.md` を該当日付でコピーする（既存のスナップショットは上書き・削除しない）
   c. 現在の `HISTORY.md` を `HISTORY.md.bak` にコピーする（互換性維持）
   d. HISTORY.md を最新の分析結果で更新:
      - 分析履歴テーブルに新しい行を追記
      - 現在のポートフォリオを上書き
      - 未実行アクションを更新（実行済みは削除、新規提案を追加）
9. メインに保存先パスのみ返す

---

## 実行時間の計算方法

- 各フェーズの所要時間 = end - start（秒単位で計算し、X分XX秒で表示）
- Phase 0a+0 合計 = max(phase_0a_end, phase_0_end) - min(phase_0a_start, phase_0_start)（並行実行のため）
- 合計 = skill_end - skill_start
- phase_3_start: timing.jsonを読み込んだ直後に現在時刻を記録
- phase_3_end / skill_end: レポート保存直前に現在時刻を記録
