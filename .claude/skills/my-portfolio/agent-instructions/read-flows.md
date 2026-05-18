# read-flows: F1 損益・資産確認 / F2 配分・乖離確認

このファイルは my-portfolio スキルの **F1 / F2**（read-only）の手順。
サブエージェントはこのファイルのみ Read すればよい（SKILL.md 不要）。

## 0. 計算前必須チェック（手順頭・スキップ禁止）

価格・損益・配分の計算をする前に必ず以下を確認する
（CLAUDE.md「株式分割の管理」/ MEMORY.md feedback_split_adjusted_calc）:

1. データ取得は **`backend/scripts/portfolio_status.py` 経由のみ**。
   同スクリプトは内部で `PortfolioService.get_holdings` /
   `get_portfolio_summary` を使用 ＝ **分割調整済み**データを返す。
2. **SQLite 直接クエリで `trades.quantity` / `unit_price` / 価格時系列を
   取得して計算に使うことを禁止**（DB 生データは分割前の元値）。
3. **データソース混在禁止**（API/サービス層出力と DB 直クエリを同じ計算内で
   混ぜない）。
4. 出力に `stock_splits` 対象銘柄が含まれる場合、評価額・損益が直感と乖離した
   ら、まず分割未調整を疑い `portfolio_status.py` 再実行で照合する。
5. ヘルパは read-only。INSERT/UPDATE/DELETE/commit は一切発生しない。

## 1. データ取得

```bash
docker compose exec -T backend python3 scripts/portfolio_status.py
# 別ユーザー指定が必要な場合のみ: --user <user_id>（既定 test）
```

- 標準出力は JSON。`resolved: false` の場合はユーザー未解決として
  「test ユーザーが見つからない」と報告し停止。
- JSON の主要キー: `summary` / `holdings` / `bucket_allocation` / `rebalance`。

## 2. F1 損益・資産（資産・損益中心）

`summary` と `holdings` を使い、以下を整形提示する。
**期間リターン・α は含めない**（weekly メールに委譲）。

出力フォーマット例:

```
## ポートフォリオ損益サマリ（test / <as_of>）

- 総資産: ¥1,760,960（評価額 ¥1,xxx,xxx + 現金 ¥xxx,xxx）
- 評価損益: +¥xx,xxx（+x.xx%）
- 保有銘柄数: N

### 銘柄別損益
| コード | 名称 | 数量 | 取得単価 | 現在値 | 評価額 | 損益 | 損益率 | 保有 |
|--------|------|------|---------|--------|--------|------|--------|------|
| XXXX | （銘柄名）… | NN | x,xxx | x,xxx | ¥xxx,xxx | +¥xx,xxx | +x.x% | NN日 |
| …（holdings の全行を JSON 値で埋める）… |

※ 数量・評価額・損益は分割調整済み（PortfolioService 出力）
```

- `summary.total_unrealized_pnl` / `total_unrealized_pnl_percent` を損益に使用。
- 各行は `holdings[]` の `quantity` / `average_cost` / `current_price` /
  `current_value` / `unrealized_pnl` / `unrealized_pnl_percent` /
  `holding_days`（または `holding_period`）。

## 3. F2 配分・乖離（A群/B群 実績vs目標・次リバランス日）

`bucket_allocation` と `rebalance` を使い整形提示する。

出力フォーマット例:

```
## 配分・乖離（test / <as_of>）

| バケット | 目標 | 実績 | 乖離(pp) |
|----------|------|------|----------|
| A群（コア・ヘッジ） | 45.0% | 24.96% | -20.04 |
| B群（日本株テーマ） | 45.0% | 42.15% | -2.85 |
| 現金 | 10.0% | 18.11% | +8.11 |
| 採用外保有 | 0.0% | 14.78% | +14.78 |

- 次回リバランス基準日: 2026-06-30（あと 43 日 / 本日はリバランス日: No）
- 想定アクション: 売り 3 件 / 買い 5 件
- 銘柄別乖離(drift_pp): rebalance.deviations を pp 降順で上位提示
```

- 目標/実績/乖離は `bucket_allocation[]` の `target_pct` /
  `actual_pct` / `drift_pp`。
- `rebalance.next_rebalance_date` / `days_to_next_rebalance` /
  `is_rebalance_day` / `sell_actions_count` / `buy_actions_count` /
  `deviations` を使用。

## 4. メインへの戻り値

- メインへは **要約 1〜数行**（例: 「F1 提示完了。総資産¥1,760,960、
  評価損益+x.xx%。詳細表はユーザー提示済み」）のみ返す。
- 整形した表本文はメインがユーザーへ提示する想定でサブエージェント出力に含める。

## 5. フォールバック

| 状況 | 対応 |
|------|------|
| `portfolio_status.py` 非ゼロ終了 / 例外 | エラー全文を要約しメインに報告。再実行を1回試行 |
| `rebalance.error` が存在 | 損益・配分のみ提示し「リバランス計算は取得失敗」と注記 |
| Docker 未起動 | `docker compose up -d` を案内（メイン側で実行） |
