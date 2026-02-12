# 議論重視モード: 独立分析 共通指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`

## データ受け渡しルール

- **入力**: `{WORK_DIR}/portfolio_data.json`, `{WORK_DIR}/market_environment.md`
- **出力**: 分析結果を `{WORK_DIR}/analyst_{a/b/c}_analysis.md` に保存
- **メインへの戻り値**: 「{analyst名}分析完了」の1行のみ。データ全文やテーブル全体を返さないこと

---

## 議論重視モードとは

議論重視モードでは、各エージェント（analyst-A, analyst-B, analyst-C）が**同じデータセット**を受け取り、独立に全項目を分析する。

**重要**: 他のエージェントと事前に相談せず、独立した判断を下すこと。

## 入力ファイル（全エージェント共通）

- `{WORK_DIR}/portfolio_data.json` - 全収集データ
- `{WORK_DIR}/market_environment.md` - 市場環境サマリー

## 出力ファイル

- analyst-A: `{WORK_DIR}/analyst_a_analysis.md`
- analyst-B: `{WORK_DIR}/analyst_b_analysis.md`
- analyst-C: `{WORK_DIR}/analyst_c_analysis.md`

## 分析項目（全エージェント共通）

1. シャープレシオ分析・リスク調整後ランキング
2. 相関分析
3. 最大ドローダウン
4. ストレスシナリオ
5. 加重平均スコア・弱い軸の特定
6. モメンタム分析
7. 低スコア銘柄の深掘り・代替銘柄提案
8. 運用会社集中リスク
9. タグベース分散度
10. 地域・セクター・テーマ別配分
11. 欠落アセットクラスの特定
12. 現金比率の妥当性評価

## 出力要件

- 各分析項目の結果に加え、**総合判断**を必ず記載する
- 総合判断には以下を含める:
  - 最も改善効果の高いアクション（トップ3）
  - 最大のリスク要因（トップ3）
  - ポートフォリオの総合評価（100点満点）
- 他のエージェントと事前に相談せず、独立した判断を下すこと

## 詳細な計算方法

各分析項目の計算方法・出力形式の詳細は、以下のファイルを参照:

- `{skill_dir}/agent-instructions/phase1-quant-analyst.md` - シャープレシオ、相関分析、ドローダウン、ストレスシナリオの計算方法
- `{skill_dir}/agent-instructions/phase1-score-analyst.md` - スコア分析、モメンタム、代替銘柄提案の手法
- `{skill_dir}/agent-instructions/phase1-allocation-analyst.md` - 運用会社集中、タグ分散、配分分析、欠落クラス特定の手法
