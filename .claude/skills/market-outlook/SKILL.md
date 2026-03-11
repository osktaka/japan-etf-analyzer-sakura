# 東証取引見通し・振り返りスキル

```yaml
---
name: market-outlook
description: 今日の東証取引見通し・振り返り（AM: 米国市場ベースの見通し / PM: 日本市場の結果レビュー）
user-invocable: true
allowed-tools: Read, Write, Bash, Agent, WebSearch, WebFetch
aliases: ["/market-outlook"]
---
```

## 概要

1日2回（AM/PM）実行に対応した東証マーケットスキル。

- **AM（見通し）**: 夜中の米国市場結果（S&P500・NASDAQ・CME日経先物・為替等）をベースに、当日の東証取引見通しを提供する
- **PM（振り返り）**: 日中の日本市場結果を集約し、値動きの要因分析・AM予想との比較を行う

一般モードとポートフォリオモードの2種類を備え、デモポートフォリオ保有銘柄への影響分析にも対応する。

## パラメータ一覧

| パラメータ | 値 | 用途 |
|-----------|-----|------|
| VIX係数（通常） | 0.05% | シナリオ分析レンジ幅 |
| VIX係数（VIX>30） | 0.04% | 高VIX時の縮小係数 |
| 横ばい判定閾値 | ±0.5% | 的中判定の横ばい基準 |
| 微小変動閾値 | ±0.1% | 判定不能の基準 |
| 時間帯判定境界 | 15:30 JST | AM/PM自動判定 |

## 使用方法

```
/market-outlook              # 時間帯自動判定（15:30前=am, 15:30以降=pm）
/market-outlook am           # AM: 今日の東証見通し
/market-outlook pm           # PM: 本日の結果・振り返り
/market-outlook portfolio    # 自動判定 + ポートフォリオモード
/market-outlook am portfolio # AM + ポートフォリオ
/market-outlook pm portfolio # PM + ポートフォリオ
```

- 引数順序は自由（`portfolio pm` も可）
- am/pm未指定時は現在時刻（JST）で自動判定（15:30が境界）
- 有効引数: `am`, `pm`, `portfolio`。不正引数は無視して警告出力
- `am pm` 同時指定: 自動判定にフォールバック

## 実行フロー

```
1. モード判定（メイン）
   ├─ timing: 引数 or 現在時刻（15:30境界）
   ├─ mode: general / portfolio
   └─ パラメータ算出: date, prev_business_day, is_trading_day, year_month, current_time
        ↓
2. データ収集+ドラフト生成（サブエージェント: general-purpose x1）
   ├─ Agent(general-purpose) で agent-instructions/market-data-collection.md に従い実行
   ├─ yfinance実行 → 定量データ確定
   ├─ WebSearch(定性のみ) → ニュース・テーマ取得
   ├─ ドラフト生成（output-formats.md テンプレートに従い）
   └─ 即時バリデーション（異常値検出 + 数値出典記録）
        ↓
3. ファイル保存（メイン）
   ├─ AM: reports/market-outlook/YYYYMMDD_am.md
   └─ PM: reports/market-outlook/YYYYMMDD_pm.md
```

## サブエージェント起動プロンプト

```
以下の指示書を読み、市場データの収集・ドラフト生成を実行してください。

指示書: .claude/skills/market-outlook/agent-instructions/market-data-collection.md
出力フォーマット: .claude/skills/market-outlook/agent-instructions/output-formats.md

パラメータ:
- timing: {timing}
- mode: {mode}
- date: {date}
- prev_business_day: {prev_business_day}
- is_trading_day: {is_trading_day}
- year_month: {year_month}
- current_time: {current_time}

タイムアウト: 300秒
```

## データ取得戦略

| タイミング | yfinance | WebSearch/WebFetch |
|-----------|----------|-------------------|
| AM | S&P500, NASDAQ, Dow, VIX, 米10年債, CME, ドル円（完全カバー） | ニュース・テーマのみ |
| PM | 日経平均, グロース250(ETF), REIT(ETF), ドル円 | TOPIX, 売買代金, セクター騰落, ニュース |

## 数値出典記録ゲート

サブエージェントはレポート内の各数値に出典を記録する。
- yfinance由来: `[yf]`
- WebSearch/WebFetch由来: `[ws]`

全数値の出典が記録されていることを検証してから返却する。

## フォールバックルール

- portfolio取得失敗時 → 一般モードとして出力し、その旨を明記する
- PM時セクター別データ不可 → セクター別騰落セクションを省略する
- 注目ETF全フォールバック失敗 → 該当セクションを省略し、`<!-- etf_recommendation_unavailable -->` を付与する
- 非営業日 → PM出力の本日結果テーブルを省略する

## ファイル保存ルール

- **AM保存先**: `reports/market-outlook/YYYYMMDD_am.md`（dateパラメータ＝実行日の日付を使用）
- **PM保存先**: `reports/market-outlook/YYYYMMDD_pm.md`
- **ファイル名の日付は実行日（処理日）**: 例えば2/21(金)にAM実行→`20260221_am.md`
- **同一timing・同日のファイルが存在する場合**: 上書きする
- **保存後**: ファイルパスをユーザーに通知する

## 完了条件

- [ ] [AM] 総合判断（上昇/下落/横ばい）が根拠付きで提示されている
- [ ] [AM] 主要指標がyfinanceで取得済み
- [ ] [AM] 注目テーマが3件以上挙げられている
- [ ] [AM] YAMLフロントマター（prediction）がファイル先頭に含まれている
- [ ] [PM] 本日の結果テーブルが正確に記載されている
- [ ] [PM] 値動きの要因分析が記載されている
- [ ] [PM] 注目ニュースが3件以上挙げられている
- [ ] [PM] AMファイル存在時: AM予想との比較セクションが含まれている
- [ ] [AM/PM] 注目ETFが3-5銘柄挙げられている（日本株ETF最低1銘柄）
- [ ] [PM] 明日の注目ETFが3-5銘柄挙げられている
- [ ] [AM/PM] ソース一覧が出力されている
- [ ] [portfolioモード] 保有銘柄への影響/結果分析が含まれている
- [ ] [AM/PM] 3行サマリーが総合判断の前に含まれている
- [ ] [AM] 為替見通し + シナリオ分析が含まれている
- [ ] [PM] 為替動向セクションが含まれている
- [ ] `reports/market-outlook/` に保存されている

出力フォーマット: → agent-instructions/output-formats.md

## 関連スキル

| スキル | 関係 |
|--------|------|
| `/etf-news` | ETF固有のニュース取得（テーマ深掘り用） |
| `/portfolio-analysis` | 詳細なポートフォリオ分析（週次運用） |
