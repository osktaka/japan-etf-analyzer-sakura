# strategy-revision: F3 銘柄変更（アシスト型）

my-portfolio スキルの **F3**。`docs/12a_戦略書改訂手順.md` の10ステップ
（事前チェック1-2／実装3-8／動作確認9-10）を再構成したアシスト型フロー。
差分案提示＋SSOT/fixture 編集まで行い、
**pytest 実行とコミットは人の確認後**（スキルは確認サマリ提示で停止）。
サブエージェントはこのファイルのみ Read すればよい（原典: `docs/12a`）。

## 0. 起動時の前提確認（一文・スキップ禁止）

着手前に必ずユーザーへ一文確認する:
「既存の改訂メモや保留中のスワップ（前回 F3 で未完了の差分・退避ファイル等）
はありますか? あれば先に教えてください」。
回答に応じて競合（同一銘柄の二重編集等）を避ける。

## 1. 事前チェック（read-only SELECT のみ）

`docs/12a` の事前チェック1〜2に対応。新銘柄が:

1. `etfs` マスタに登録済みか
2. `price_histories` に直近データがあるか

を **read-only SELECT** で確認する（書き込み・JPX 同期は行わない）:

```bash
docker compose exec -T backend python3 -c "
import sys; sys.path.insert(0,'/app')
from src.app import create_app
from src.repositories import ETFRepository
app=create_app()
with app.app_context():
    r=ETFRepository(); print(r.get_by_codes(['<NEW_CODE>']))
"
```

- **未登録の場合**: 「`<code>` は etfs/price_histories に未登録。JPX 同期
  （状態変更）は本スキルの範囲外」と報告し、**人手に回して停止**。
- 登録済みなら次へ。

## 2. 差分案提示 → AskUserQuestion で承認

現行 `docs/12_personal_strategy.md` の frontmatter を Read し、以下の差分案を
構造化提示する（`docs/12a` ステップ3〜5に対応）:

- `target_holdings`: 追加/削除/置換する銘柄（code・name・bucket・weight_pct）
- `target_buckets`: group_a/group_b/cash の weight_pct（変更時）
- §2 全体方針表（本文 markdown）の更新箇所
- `revision`（日付）/ `revision_history` 追記文

整合性ルール（`docs/12a` の落とし穴を反映）:
- 各 bucket 内の `weight_pct` 合計＝`target_buckets[bucket].weight_pct`
- 全 `target_holdings` weight_pct 合計 + cash = 100
- A群×B群で同一銘柄が重複する場合は按分ルールに従い解消

差分案を **AskUserQuestion** で承認/修正/中止に分岐。承認まで一切編集しない。

## 3. 承認後の編集（ホスト側 Edit）

承認された差分のみ、以下を Edit する（`docs/12a` ステップ3〜6,8）。
コンテナ read-only マウントを避けるため **ホスト側 Edit ツール**で編集:

| ファイル | 編集内容 |
|---------|---------|
| `docs/12_personal_strategy.md` | frontmatter（target_holdings/target_buckets/revision/revision_history）＋§2方針表 |
| `docs/06b_メール通知仕様.md` | 改訂履歴に追記 |
| `backend/tests/unit/services/test_strategy_loader.py` | yaml fixture と期待値 |
| `backend/tests/unit/services/test_daily_advisor_service.py` | yaml fixture |
| `backend/tests/unit/services/test_notification_renderer.py` | アサーション内文字列（ラベル変更時のみ） |
| `backend/tests/integration/test_portfolio_rebalance_strategy_integration.py` | 採用銘柄数とコード集合 |

- 各 fixture の既存 yaml ブロック構造に合わせ、整合性ルール（手順2）を維持。
- 編集は承認された差分の範囲に限定。無関係な箇所は変更しない。

## 4. 確認サマリ提示で停止（pytest/commit は人手）

編集完了後、以下を **確認サマリ**としてユーザーに提示し **停止**する
（`docs/12a` ステップ7,9,10 + 関連コミットは人手）:

```
## F3 戦略改訂 完了（編集のみ・テスト/コミット未実行）

### 変更ファイル一覧
- docs/12_personal_strategy.md
- docs/06b_メール通知仕様.md
- backend/tests/unit/services/test_strategy_loader.py
- backend/tests/unit/services/test_daily_advisor_service.py
- backend/tests/unit/services/test_notification_renderer.py（ラベル変更時）
- backend/tests/integration/test_portfolio_rebalance_strategy_integration.py

### 次アクション（すべて人手で実施してください）
1. スナップショット再生成（docs/12a ステップ7のコマンド）
2. フル pytest（backend テストスイート）
3. evening 実行 → メール本文確認（docs/12a ステップ9）
4. morning 実行 → 前夜決定事項リマインダー確認（docs/12a ステップ10）
5. 問題なければ git commit（--no-verify 禁止）

※ pytest・コミットは本スキルでは実行しません。
```

- このサマリ提示をもって F3 は終了。pytest/commit/スナップショット再生成は
  **絶対に自動実行しない**（境界を明示）。

## 5. メインへの戻り値

要約 1〜数行（例: 「F3: 6ファイル編集完了。確認サマリ提示で停止。
pytest/commit 未実行（人手案内済）」）。

## 6. フォールバック

| 状況 | 対応 |
|------|------|
| 新銘柄未登録 | 手順1で停止し人手（JPX 同期）へ |
| 差分整合性違反（weight 合計不一致等） | 編集前に検出し再提案。承認なしで編集しない |
| ユーザーが中止 | 編集を一切行わず終了 |
