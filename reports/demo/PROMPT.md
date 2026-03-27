# デモユーザー ポートフォリオ分析プロジェクト

## プロジェクト概要

デモユーザー（user_id=`demo`）のETFポートフォリオを日次で分析・運用するプロジェクト。
未ログインユーザーがMyPageのプレビューとして閲覧するデモデータを、定期的に分析・最適化する。

## 認証情報

| 項目 | 値 |
|------|-----|
| user_id | `demo` |
| password | `D3m0$ecur3!Passw0rd#2026` |

## 初回ルール

取引履歴がない場合（初回構築時）:

1. **資金**: 100万円でポートフォリオを新規構築する
2. **デモデータのリセット**: 既存デモデータのリセットが必要な場合は `backend/scripts/seed_demo_data.py` を修正・実行する
3. 構築後、HISTORY.md の投資方針・ポートフォリオ状態を記入する

## 日次分析フロー

### 1. 事前準備

1. 本ファイル（PROMPT.md）を読む
2. `reports/demo/HISTORY.md` を読む（ファイルが存在しない場合は初回として扱う）
3. HISTORY.md から以下を把握する:
   - 過去の分析履歴
   - 未実行アクション
   - 現在のポートフォリオ状態

### 2. 分析実行

`/portfolio-analysis` スキルを実行する（demoユーザー指定、モード: **normal**）。

- v1（従来方式）: `/portfolio-analysis` -- 3モード選択（speed/normal/debate）、5ペルソナ独立分析
- v2（ブレインストーミング方式）: `/pf-v2` -- 3並列会議+マージ統合、モード指定不要
- デフォルトで v2（`/pf-v2`）を使用する

### 2.5. 取引実行（条件付き）

分析結果にリバランス提案（売買アクション）が含まれ、以下の条件を満たす場合に自動実行する:

1. **事前チェック**:
   - `GET /api/v1/demo/portfolio` で現金残高・総資産を確認
   - `GET /api/v1/demo/portfolio/holdings` で保有銘柄・数量を確認
   - 買い: 現金残高 >= 数量 × 価格、かつ金額 <= 総資産の20%
   - 売り: 保有数量 >= 売却数量

2. **実行（開発→本番の順）**:
   ```bash
   # 開発環境
   curl -X POST http://localhost:8902/api/v1/demo/trades \
     -H "Content-Type: application/json" \
     -d '{"etf_code":"XXXX","trade_type":"buy","quantity":N,"price":NNN.N,"trade_date":"YYYY-MM-DD","memo":"[auto] 理由"}'

   # 開発が成功した場合のみ本番環境にも実行
   curl -X POST https://kima3.net/japan-etf-analyzer/api/v1/demo/trades \
     -H "Content-Type: application/json" \
     -d '（同じリクエストボディ）'
   ```
   - 入出金が必要な場合は `POST /api/v1/demo/cash-flows` も同様に両環境へ送信

3. **環境一致チェック**（全取引・入出金の登録完了後に1回実行）:
   ```bash
   # 開発環境のポートフォリオ取得
   curl -s http://localhost:8902/api/v1/demo/portfolio

   # 本番環境のポートフォリオ取得
   curl -s https://kima3.net/japan-etf-analyzer/api/v1/demo/portfolio
   ```
   - 両環境の `total_asset`、`cash_balance`、`holdings_count` が一致していることを確認
   - 不一致の場合は警告を出力し、差分を報告する（自動修正はしない）

4. **実行後**: HISTORY.md の未実行アクションを実行済みに更新し、取引詳細（銘柄、数量、価格）を記載

### 3. レポート保存

分析レポートはスキルの既定動作により `reports/demo/` に保存される:

```
reports/demo/YYYYMMDD_demo.md
```

→ **次のアクション**: 記事を作成する場合は `/publish-report` でドラフトを作成してください。分析のみで記事化しない場合は HISTORY.md を直接更新してください。

### 4. 記事ドラフト作成（demoのみ）

`/publish-report` スキル（ドラフトモード）でノート記事のドラフトを作成する。

- ドラフトは `reports/demo/drafts/YYYYMMDD_draft.md` に保存される
- **HISTORY.md は触らない**（ドラフト段階では履歴を更新しない）
- 何度でも作り直し可能（上書き保存）
- cronスクリプト（`scripts/cron-portfolio-analysis.sh`）実行時は、Step 3の後に `/publish-report auto` が自動実行され、ドラフトが作成される

→ **次のアクション**: ドラフトを確認し、記事確定へ進む場合は `/publish-report confirm` と指示してください。修正が必要な場合は再度 `/publish-report` を実行してください。

### 5. 記事確定・公開（demoのみ）

ユーザーの確定指示後、`/publish-report confirm` で記事を確定・公開する。

確定時に以下が実行される:

1. ドラフトを `publish_note.py` でDB投入
2. ビルド確認
3. HISTORY.md 更新:
   - **スナップショット保存**: 当日のスナップショットが無ければ `HISTORY.md` を `history/YYYYMMDD.md` として保存
   - **バックアップ**: `HISTORY.md` を `HISTORY.md.bak` にコピー
   - **分析履歴テーブル**: 新しい行を追記
   - **現在のポートフォリオ**: 最新の保有状態で上書き
   - **未実行アクション**: 今回の提案で更新（実行済みは削除、新規提案を追加）
4. `drafts/` のドラフトファイルを削除

※ 分析結果を戻したい場合は `HISTORY.md.bak` から復元できる
※ 過去の分析結果を参照したい場合は `history/` ディレクトリのスナップショットを確認できる

→ **次のアクション**: 変更をコミットする場合は `/commit` と指示してください。

## 重要ルール

1. **取引の自動実行** -- Claude Code は分析結果に基づき、デモ用API経由で取引を自動実行できる。以下の条件を遵守すること:
   - 買い付け前に現金残高を確認（`GET /api/v1/demo/portfolio`）し、買い付け金額が現金残高を超えないこと
   - 売却前に保有数量を確認（`GET /api/v1/demo/portfolio/holdings`）し、売却数量が保有数量以下であること
   - memoフィールドに `[auto]` プレフィックスと実行理由を記載すること
   - 1日の取引回数は最大5件まで
   - 1回の取引金額は総資産の20%以下であること
   - 取引実行後、HISTORY.md の未実行アクションを更新すること
2. **分析前に必ず HISTORY.md を読み込むこと** -- 過去の文脈なしに分析すると一貫性が失われる
3. **ドラフト→確定の原則** -- 記事はまずドラフトとして作成し、ユーザーの確定指示があるまで HISTORY.md を更新しない。HISTORY.md の更新と history/ のスナップショット作成は記事確定時のみ実行する
4. **分析のみ（記事化なし）の場合** -- 分析レポート生成後に HISTORY.md を直接更新してよい（記事化しない場合はドラフトフローは不要）
