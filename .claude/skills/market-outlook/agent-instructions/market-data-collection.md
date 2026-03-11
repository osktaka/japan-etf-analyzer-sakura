# 市場データ収集・ドラフト生成 指示書

## 前提（共通）

- タイミング: `{timing}`（`am` または `pm`）
- モード: `{mode}`（`general` または `portfolio`）
- 日付: `{date}`、前営業日: `{prev_business_day}`
- 営業日フラグ: `{is_trading_day}`
- 年月: `{year_month}`、現在時刻: `{current_time}`

## データ取得フロー

### Step 0: yfinanceによる定量データ取得（AM/PM共通）

```bash
# AM実行時
docker compose exec backend python scripts/market_data_quick.py
# PM実行時
docker compose exec backend python scripts/market_data_quick.py --pm
```

- JSON出力を解析し、取得成功した指標をレポートに使用
- 失敗した指標（errorsに記載）のみWebFetchで補完
- スクリプト実行自体が失敗した場合はStep 1のWebSearchで定量データも取得

### Step 1: WebSearch（定性情報のみ）

**AM（timing=am）**:

| クエリ | 検索文字列 |
|--------|-----------|
| ニュース・テーマ | `日本 経済 マーケット 見通し 重要ニュース {date}` |

※ S&P500/NASDAQ/Dow等の定量データはyfinanceで取得済みのためWebSearch不要

**PM（timing=pm）**:

| クエリ | 検索文字列 |
|--------|-----------|
| 東証結果・ニュース | `日経平均 TOPIX 東証 業種別騰落 売買代金 {date}` |

※ PM時のTOPIX、売買代金、セクター騰落はyfinance非対応のためWebSearchで取得

**PM時のWebFetch補完**:

| 不足データ | WebFetch先 |
|-----------|-----------|
| TOPIX | https://finance.yahoo.co.jp/quote/998405.T |
| セクター別騰落 | Yahoo!ファイナンス 業種別株価指数 |
| 売買代金 | Yahoo!ファイナンス 市場概況ページ |

### Step 2: portfolioモード時のAPI取得

`{mode}` が `portfolio` の場合のみ:

```bash
curl -s http://localhost:8902/api/v1/demo/portfolio/holdings
```

保有比率上位5銘柄に絞る。API失敗時は `<!-- portfolio取得失敗 -->` を出力末尾に付与。

### Step 3: 注目ETF収集

AM/PM共通:

1. **keyword検索**: `curl -s "http://localhost:8902/api/v1/etfs?keyword={テーマ}&momentum_labels=上昇加速,上昇維持&sort=return_1m&order=desc&limit=5"`
2. **tag_idsフォールバック**: `curl -s "http://localhost:8902/api/v1/tags"` → tag_idで再検索
3. **tag-momentumフォールバック**: `curl -s "http://localhost:8902/api/v1/market/tag-momentum"`
4. **最終フォールバック**: セクション省略

日本株ETF最低1銘柄必須。3-5銘柄を目標。
PM時はStep 3で「今日の注目ETF」と「明日の注目ETF」の両方を収集。

### Step 4: ドラフト生成

output-formats.md のテンプレートに従いドラフトを生成する。

- 出力フォーマット参照: `agent-instructions/output-formats.md`
- timingに応じてAM/PMテンプレートを選択
- modeに応じてポートフォリオセクションを追加/省略

## 異常値検出（簡易ルール）

| 指標 | 閾値 | 対応 |
|------|------|------|
| S&P500/NASDAQ/Dow | 前日比±5%超 | 原因を1文添付 |
| 日経平均 | 前日比±4%超 | 原因を1文添付 |
| ドル円 | 前日比±2円超 | 原因を1文添付 |
| VIX | 50超 | 警戒水準と明記 |

※ 旧正確性チェック（終値確定判定→複数ソースクロスチェック→異常値検出の3段階）は廃止。
yfinance値をそのまま信頼し、異常値のみフラグ。

## 数値出典記録

レポート内の各数値について出典を内部的に記録:

- yfinance由来: `[yf]`
- WebSearch/WebFetch由来: `[ws]`

全数値の出典が記録されていることを検証してから返却。

## 時間帯ルール

### AM時間帯

| 実行時刻(JST) | 米国市場 | 東証データ |
|--------------|---------|-----------|
| 6:00-8:00 | 前夜終値（確定） | 前営業日終値 |
| 8:00-9:00 | 前夜終値（確定） | 前営業日終値（東京時間変動あり注記） |
| 9:00-15:30 | 前夜終値 | 取引中（非推奨・警告） |

### PM時間帯

| 実行時刻(JST) | 東証データ |
|--------------|-----------|
| 15:30-翌0:00 | 当日終値 |
| 0:00-6:00 | 前営業日終値 |
| 6:00-15:30 | 取引中（非推奨・警告） |

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| yfinanceスクリプト失敗 | WebSearchで全指標取得（従来モード） |
| WebSearch結果0件 | クエリを変えて再検索（日付なし版） |
| WebSearch完全失敗 | WebFetchで直接アクセス |
| セクター別騰落取得不可 | セクション省略 + `<!-- sector_data_unavailable -->` |
| 注目ETF全フォールバック失敗 | セクション省略 |
| ポートフォリオAPI失敗 | `<!-- portfolio取得失敗 -->` |

リトライ上限: 同一URLへの3回目のアクセスは禁止

## 出力

output-formats.md テンプレートに従った完成レポートを直接返却する。ファイル保存はメインエージェントが行う。
