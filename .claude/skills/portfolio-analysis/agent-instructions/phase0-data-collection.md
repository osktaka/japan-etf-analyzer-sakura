# Phase 0: データ収集 指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`
- 認証情報: user_id=`{USER_ID}`, password=`{PASSWORD}`（メインエージェントから渡される）
- APIベースURL: `http://localhost:8902`

## データ受け渡しルール

- **入力**: なし（API/DB直接アクセス）
- **出力**:
  - `{WORK_DIR}/00_portfolio_data.json` — 全収集データ
  - `{WORK_DIR}/00_portfolio_reference.md` — セクション1・11.2用markdownテーブル(プログラマティック生成。Phase 3+4統合エージェントがそのまま転記する)
- **メインへの戻り値**: 完了メッセージ1行のみ。データ全文やテーブル全体を返さないこと

## スキップ判断基準

このフェーズにスキップ条件はない。常に実行する。

## 株式分割調整データの検証（必須）

**背景**: 2026-02-14に、DBクエリ経由で取得した数量・取得単価が株式分割調整前のデータとなり、API（PortfolioService）経由の分割調整済みデータと不一致が発生した。これにより総資産が約3万円過小評価され、レポート全体を破棄する事態となった。

**原則**: 保有銘柄の数量・取得単価・評価額・損益率は**必ずAPI `/api/v1/portfolio/holdings` のレスポンスを正とする**。DBの `trades` テーブルを直接クエリして数量・単価を取得してはならない。

> **補足**: 「DB直接クエリ禁止」の対象は `trades` テーブルのみ。performance_cache, score_cache, etfs, tags, price_histories はキャッシュ/マスタデータであり、株式分割調整の影響を受けないため直接クエリを許容する。

**検証手順**: データ収集完了後、以下を実行する。

1. `00_portfolio_data.json` の `holdings` セクションから各銘柄の `quantity`, `average_cost`, `current_price`, `current_value` を抽出
2. `quantity × current_price = current_value` が成立することを確認
3. 全銘柄の `current_value` 合計 + `cash_balance` = `summary.total_asset` が成立することを確認
4. 不一致がある場合、エラーメッセージを出力してスクリプトを停止する（不正確なデータでの分析を防止）

**確認コード例**:

> **注**: この検証ロジックは `phase0-collection-template.py` に組込済み。テンプレートを使用する場合は手動追加不要。テンプレートを使わず独自実装する場合のみ、以下のコードを必ず組み込むこと。

```python
# データ収集後の検証
holdings_data = holdings.get('data', [])
summary_data = summary.get('data', {})
cash = summary_data.get('cash_balance', 0)
total_asset_from_summary = summary_data.get('total_asset', 0)

total_current_value = 0
for h in holdings_data:
    qty = h.get('quantity', 0)
    price = h.get('current_price', 0)
    cv = h.get('current_value', 0)
    calc_cv = qty * price
    if abs(calc_cv - cv) > 1:  # 1円以上の誤差
        print(f"警告: {h['etf_code']} の評価額不整合: {qty}口×{price}円={calc_cv}円 ≠ {cv}円")
    total_current_value += cv

calc_total = total_current_value + cash
if abs(calc_total - total_asset_from_summary) > 10:  # 10円以上の誤差
    print(f"エラー: 総資産不整合: 銘柄合計{total_current_value}円 + 現金{cash}円 = {calc_total}円 ≠ サマリー{total_asset_from_summary}円")
    sys.exit(1)
print(f"検証OK: 総資産{total_asset_from_summary:,.0f}円（銘柄{total_current_value:,.0f}円 + 現金{cash:,.0f}円）")
```

### 禁止パターン（データ収集時）

以下のDB直接クエリパターンは**絶対に使用禁止**。株式分割調整前のデータが返され、レポート全体が不正確になる:

- `SELECT * FROM trades` — 分割前の元の数量・単価が返される
- `SELECT quantity, price FROM trades` — 同上
- tradesテーブルへの任意のSELECT文
- portfolioテーブルのquantity/average_costカラムの直接取得（APIを経由すること）

**正しい取得方法**: `/api/v1/portfolio/holdings` API経由で取得する。APIはSplitAdjustmentServiceを経由して分割調整済みデータを返す。

## `_metadata`セクションの出力（必須）

`00_portfolio_data.json` の先頭に `_metadata` キーを追加し、各データセクションのスキーマ情報を含めること。アナリストエージェントはこの `_metadata` を最初に読み、正しいフィールド名を確定してからスクリプトを書く。

**`_metadata`に含める情報（各データセクション）**:
- `count`: データ件数（`len(data)`）
- `columns`: 最初のレコードのキー一覧
- `sample`: 最初のレコードをそのまま出力
- `holding_count`: 保有銘柄数（`len(etf_codes)`、allocation-analyst起動判断用）
- セクション固有の情報（`perspectives`, `periods`等はユニーク値を抽出）

### データ仕様

| セクション | 取得頻度 | 期間 | 期待件数（5銘柄の場合） |
|-----------|---------|------|----------------------|
| `holdings` | リアルタイム | - | 保有銘柄数（5件） |
| `summary` | リアルタイム | - | 1件 |
| `valuation_history` | 日次データ | 3年分（`period=3y`） | 約750件 |
| `performance_cache` | キャッシュ | 8期間×銘柄数 | 約40件 |
| `score_cache` | キャッシュ | 6視点×銘柄数 | 約30件 |
| `price_data` | 日次データ | 直近13ヶ月 | 約65件（月次リターン計算用、後方互換） |
| `price_data_daily_30d` | 日次データ | 直近30日 | 約150件（OHLCV、ATR/出来高用） |
| `price_data_close_250d` | 日次データ | 直近14ヶ月（250営業日） | 約1250件（close、200MA用） |
| `dividend_data` | yfinance | 3年分 | 銘柄別年度別配当合計（取得失敗時null） |
| `etf_data` | マスタ | - | 保有銘柄数（5件） |
| `tag_data` | マスタ | - | 約25件 |

### `_data_status`セクション（必須）

`_metadata` に `_data_status` キーを追加し、全データソースの取得状態を記録すること。Phase 1アナリストはこの情報を使ってスキップ判断を行う。

**記録対象**: holdings, summary, valuation_history, performance_cache, score_cache, etf_data, tag_data, price_data, price_data_daily_30d, price_data_close_250d, dividend_data, recommendations_balance, recommendations_dividend, recommendations_low-cost, compare_performance, compare_scores

**ステータス値**:
- `"ok"`: 正常取得（件数付き）
- `"empty"`: HTTP 200だがデータが空
- `"error"`: 取得失敗（エラー詳細付き）

**出力例**:
```json
{
  "_metadata": {
    "score_cache": {
      "count": 30,
      "perspectives": ["balance", "dividend", "low-cost", "stability", "volume", "growth"],
      "axes": ["dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"],
      "columns": ["etf_code", "perspective", "total_score", "..."],
      "sample": { "etf_code": "1475", "perspective": "balance", "total_score": 76.4 }
    },
    "performance_cache": {
      "count": 40,
      "periods": ["1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"],
      "columns": ["etf_code", "period", "return_rate", "volatility", "regression_rate"],
      "sample": { "etf_code": "1475", "period": "1y", "return_rate": 0.4014 }
    },
    "etf_codes": ["1475", "1329", "1615", "1489", "1597"],
    "holding_count": 5,
    "_data_status": {
      "holdings": {"status": "ok", "count": 5},
      "summary": {"status": "ok", "count": 1},
      "valuation_history": {"status": "ok", "count": 742},
      "performance_cache": {"status": "ok", "count": 40},
      "score_cache": {"status": "ok", "count": 30},
      "etf_data": {"status": "ok", "count": 5},
      "tag_data": {"status": "ok", "count": 25},
      "price_data": {"status": "ok", "count": 65},
      "price_data_daily_30d": {"status": "ok", "count": 150},
      "price_data_close_250d": {"status": "ok", "count": 1250},
      "dividend_data": {"status": "ok", "count": 5},
      "recommendations_balance": {"status": "ok", "count": 10},
      "recommendations_dividend": {"status": "ok", "count": 10},
      "recommendations_low-cost": {"status": "error", "http_status": 500, "error": "Internal Server Error"},
      "compare_performance": {"status": "ok", "count": 1},
      "compare_scores": {"status": "ok", "count": 1}
    }
  },
  "holdings": { "..." : "..." },
  "..."
}
```

---

## 追加データ取得仕様（OHLCV + 配当）

### `price_data_daily_30d`（直近30日OHLCV）

- **取得元**: `price_histories` テーブル
- **カラム**: `etf_code, date, open, high, low, close, volume`
- **期間**: `date >= date('now', '-30 days')`
- **用途**: Phase 0.5のATR(14)計算、出来高異常検知
- **注意**: `volume` カラムにNULLがある場合も取得する（Phase 0.5側でフォールバック処理）

### `price_data_close_250d`（直近14ヶ月close）

- **取得元**: `price_histories` テーブル
- **カラム**: `etf_code, date, close`
- **期間**: `date >= date('now', '-14 months')`（250営業日を確保するため14ヶ月）
- **用途**: Phase 0.5の200日移動平均防御シグナル計算
- **後方互換**: 既存 `price_data`（13ヶ月close）はそのまま維持する。`price_data_close_250d` は追加キーとして並存

### `dividend_data`（3年分配当データ）

- **取得元**: yfinance `ticker.dividends`（外部API）
- **期間**: 3年分
- **集計**: 銘柄別・年度別の配当合計
- **出力形式**: `{"1475": {"2024": 45.0, "2023": 42.0, "2022": 40.0}, ...}`
- **フォールバック**: yfinance 0.1.63で `ticker.dividends` 取得失敗時は `dividend_data: null` を設定し、`_data_status` に `{"status": "error", "error": "配当データ取得失敗"}` を記録。この場合、Phase 0.5の分配金Zスコア（項目10）は一括スキップされる
- **注意**: 配当データ取得は `try/except` で囲み、1銘柄の失敗が他銘柄に影響しないようにする

### `00_portfolio_data.json` の出力構造（追加分）

```json
{
  "_metadata": {
    "price_data_daily_30d": {"count": 150, "columns": ["etf_code", "date", "open", "high", "low", "close", "volume"], "sample": {...}},
    "price_data_close_250d": {"count": 1250, "columns": ["etf_code", "date", "close"], "sample": {...}},
    "dividend_data": {"count": 5, "columns": ["etf_code"], "sample": {"1475": {"2024": 45.0, "2023": 42.0}}},
    "_data_status": {
      "price_data_daily_30d": {"status": "ok", "count": 150},
      "price_data_close_250d": {"status": "ok", "count": 1250},
      "dividend_data": {"status": "ok", "count": 5}
    }
  },
  "price_data": [...],
  "price_data_daily_30d": [...],
  "price_data_close_250d": [...],
  "dividend_data": {...}
}
```

> **注**: Phase 1ペルソナ（debateモード）はこれらの生データを直接参照しない。Phase 0.5が計算済みテーブル（`05_shared_calculations.md`）に集約し、Phase 1は計算済みテーブルのみ参照する。normalモードではPhase 0.5が実行されないため、Phase 1アナリストが生データから自力計算する。

---

## スクリプトテンプレート

実装時は以下のテンプレートを参照:
`{skill_dir}/agent-instructions/phase0-collection-template.py` (出力先: `{WORK_DIR}/00_portfolio_data.json`, `{WORK_DIR}/00_portfolio_reference.md`)

プレースホルダーの置換:
- `{USER_ID}` → 認証ユーザーID
- `{PASSWORD}` → 認証パスワード
- `{WORK_DIR}` → 作業ディレクトリパス
