# Phase 0: 市場スナップショット（共通・1回のみ）

## 目的

target_holdings + watchlist 全銘柄の Phase 1 評価で**共通参照**できる、
当日（または直近営業日）の市場マクロ環境を1ファイルにまとめる。Phase 1
側で同一テーマを再検索するのを防ぎ、総 WebSearch 回数を `calc_params.json`
の `web_search.total_budget_target`（=30回）以内に抑える。

## 入力パラメータ

| パラメータ | 説明 | 例 |
|------------|------|-----|
| `WORK_DIR` | 作業ディレクトリ | `.tmp/etf-rating_20260522` |
| `CALC_PARAMS_PATH` | 共通閾値 JSON | `.claude/skills/etf-rating/calc_params.json` |
| `RUN_DATE` | 実行日（YYYY-MM-DD） | `2026-05-22` |

## 検索バジェット

`calc_params.json` の `web_search.phase0_shared_search_budget`（既定15回）を上限とする。
超過時は警告を出力ファイル冒頭に記載して続行。

## 手順

### 1. 設定読み込み

- `calc_params.json` を Read し、`web_search.phase0_shared_search_budget` を取得
- 検索カウンタを初期化（`search_count = 0`）

### 2. マクロ環境の取得（WebSearch / WebFetch）

#### 2a. 共通必須15指標（1回の Phase 0 で必ず全件取得）

以下の15指標を最優先で取得する。各指標1〜2クエリで完結させ、**合計検索回数を15回以内**に収める（バジェット = `phase0_shared_search_budget`）。

| # | 指標 | カテゴリ | WebSearch クエリ例 | 想定出典 |
|---|------|----------|-------------------|----------|
| 1 | Brent 原油 | コモディティ | `Brent crude oil price today` | OilPrice / Reuters |
| 2 | WTI 原油 | コモディティ | `WTI crude oil price today` | OilPrice / EIA |
| 3 | JKM LNG | コモディティ | `JKM LNG spot price latest` | S&P Platts / Reuters |
| 4 | 銅 (LME) | コモディティ | `LME copper price USD per pound today` | LME / Reuters |
| 5 | 鉄鉱石 (62% Fe) | コモディティ | `iron ore 62% Fe price Platts today` | Platts / SMM |
| 6 | 一般炭 (Newcastle) | コモディティ | `Newcastle thermal coal price latest` | Argus / GlobalCoal |
| 7 | USD/JPY | 為替 | `USDJPY exchange rate today` | yfinance / Reuters |
| 8 | EUR/USD | 為替 | `EURUSD exchange rate today` | yfinance / Reuters |
| 9 | FF金利（FRB） | 米国マクロ | `Federal Reserve current FF rate target range 2026` | FRB / WSJ |
| 10 | 米10年債利回り | 米国マクロ | `US 10 year treasury yield today` | CNBC / Bloomberg |
| 11 | 米CPI（直近） | 米国マクロ | `US CPI latest release year over year` | BLS / Reuters |
| 12 | ISM 製造業 PMI | 米国マクロ | `ISM manufacturing PMI latest` | ISM |
| 13 | 中国製造業 PMI | 中国マクロ | `China Caixin manufacturing PMI latest` (and NBS) | Caixin / NBS |
| 14 | VIX | 株式市場 | `VIX index level today` | CBOE |
| 15 | 地政学要約 | 地政学 | `Middle East tensions Ukraine Taiwan headlines today` | Reuters |

**運用ルール**:
- 1指標あたりの WebSearch は **原則1回**。失敗時のみリトライ1回（計2回まで）
- 引用元 URL は本文「主要指標サマリ」表の出典列に明記
- 検索クエリは英語推奨（一次情報源のヒット率が高い）

#### 2b. 補助カテゴリ（バジェットに余裕がある場合のみ）

| # | カテゴリ | 主要指標 |
|---|----------|----------|
| A | 日本マクロ | 日銀政策金利・YCC・コアCPI・国債利回り |
| B | 株式ベンチマーク | ^N225 / TOPIX / S&P500 / NASDAQ 直近値・前日比 |
| C | テーマ動向 | 新NISA資金フロー・半導体サイクル・銀行株動向（topix-17 系） |
| D | 為替補助 | EUR/JPY・人民元 |

合計検索回数が `phase0_shared_search_budget`（15回）を超える見込みなら 2b はスキップ。
2a の15指標を全件取得することを優先。

### 3. 株価ベンチマーク

- ^N225 / TOPIX / S&P500 の直近終値と前日比、月初比、年初来を記録
- 取引時間中（東証 9:00-15:30 JST）に実行された場合は「前営業日終値」と明記

### 4. リスクオン/オフ判定

| 判定材料 | リスクオン | リスクオフ |
|----------|------------|------------|
| VIX | <15 | >25 |
| USD/JPY | 円安方向 | 円高方向 |
| 米10年債 | 上昇 | 急低下 |
| ^N225 | 月次プラス | 月次マイナス |

総合判定: **リスクオン / 中立 / リスクオフ** のいずれか。

### 5. 出力ファイル生成

`{WORK_DIR}/00_market_snapshot.md` を Write で作成。

#### 出力フォーマット

```markdown
# 市場スナップショット（{RUN_DATE}）

**取得時刻**: {ISO8601}
**WebSearch 検索回数**: {search_count} / {budget}
**市況判定**: リスクオン / 中立 / リスクオフ

## 共通必須15指標（Phase 1 全銘柄が共通参照）

| # | 指標 | 値 | 単位 | 前日比 / 直近トレンド | 出典 |
|---|------|----:|------|----:|------|
| 1 | Brent 原油 | XX.X | USD/bbl | +X.XX% | URL |
| 2 | WTI 原油 | XX.X | USD/bbl | +X.XX% | URL |
| 3 | JKM LNG | XX.X | USD/MMBtu | +X.XX% | URL |
| 4 | 銅 (LME) | X.XX | USD/lb | +X.XX% | URL |
| 5 | 鉄鉱石 62%Fe | XXX | USD/t | +X.XX% | URL |
| 6 | 一般炭 Newcastle | XXX | USD/t | +X.XX% | URL |
| 7 | USD/JPY | XXX.XX | - | +X.XX% | URL |
| 8 | EUR/USD | X.XXXX | - | +X.XX% | URL |
| 9 | FF金利 | X.XX-X.XX | % | （前回会合差分） | URL |
| 10 | 米10年債利回り | X.XX | % | +X bp | URL |
| 11 | 米CPI（YoY） | X.X | % | （前月差分） | URL |
| 12 | ISM 製造業 PMI | XX.X | - | （前月差分） | URL |
| 13 | 中国製造業 PMI | XX.X | - | （Caixin/NBS両方記載） | URL |
| 14 | VIX | XX.X | - | +X.X | URL |
| 15 | 地政学要約 | - | - | （3行サマリ） | URL |

## 主要株価ベンチマーク（補助）

| カテゴリ | 指標 | 値 | 前日比 | 出典 |
|----------|------|----:|----:|------|
| 株式 | ^N225 | XX,XXX.XX | +X.XX% | yfinance/web |
| ...

## マクロ環境

### 米国
- FF金利: ...
- コアPCE: ...

### 日本
- 日銀政策金利: ...

### 中国
- ...

## 為替

| ペア | 終値 | 前日比 | 直近の論点 |

## コモディティ

| 商品 | 終値 | 前日比 | 直近の論点 |

## 地政学・テーマ

- 中東: ...
- 半導体サイクル: ...

## Phase 1 への申し送り

各銘柄評価で参照すべきポイントを箇条書きで3〜5項目:
- コモディティ動向は商社/エネルギー銘柄（1629/1618）の上昇条件 A-1/A-8 に直結
- 円高転換リスクは輸出関連銘柄の下落条件 B-2 で参照
- ...
```

## 出力

| ファイル | 内容 |
|----------|------|
| `{WORK_DIR}/00_market_snapshot.md` | 上記フォーマット |

## メインへの戻り値

完了時1行:
```
Phase 0 完了（検索回数: {N}回, 市況: {リスクオン|中立|リスクオフ}）
```

失敗時1行（自己修正1回試行後）:
```
Phase 0 失敗: {理由}。Phase 1 は内部簡易検索へ縮退推奨
```

## 注意事項

- 個別銘柄固有のニュース（例: 1629 の決算）は Phase 1 で扱う。Phase 0 は**マクロのみ**
- 取得失敗カテゴリは「{カテゴリ}: 取得失敗（理由）」と明記して続行
- WebSearch 検索クエリ数が予算超過しそうな場合は途中で停止し、その旨を明記
