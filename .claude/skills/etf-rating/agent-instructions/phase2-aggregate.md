# Phase 2: 集計サマリ

## 目的

Phase 1 で生成された全銘柄の評価レポート（および履歴 jsonl）を統合し、
本日の総評・スコアランキング・ハイライト（前日比±5pp 超）・観点鮮度警告
を1ファイルにまとめる。Phase 3 メールペイロード生成と運用者の日次確認の両方で参照される。

## 入力パラメータ

| パラメータ | 説明 | 例 |
|------------|------|-----|
| `WORK_DIR` | 作業ディレクトリ | `.tmp/etf-rating_20260522` |
| `CALC_PARAMS_PATH` | 共通閾値 JSON | `.claude/skills/etf-rating/calc_params.json` |
| `RUN_DATE` | 実行日（YYYY-MM-DD） | `2026-05-22` |
| `HISTORY_DIR` | 採点履歴ディレクトリ | `data/etf-rating/history/` |

## 手順

### 1. 入力収集

- `{WORK_DIR}/10_rating_*_summary.json` を Glob で列挙し、全てを Read
- `{WORK_DIR}/00_market_snapshot.md` を Read（市況判定の引用に使う）
- `CALC_PARAMS_PATH` を Read（閾値取得）

### 2. ランキング作成

ネット中期スコア降順で並べた一覧表を作成:

| 順位 | コード | 銘柄名 | ネット | 上昇W | 下落W | 先取り | 後追い | 前日比 |

### 3. ハイライト抽出

`calc_params.json` の `drift_alert.score_change_pp_threshold`（既定5pp）超の銘柄を抽出:

- **強気転換** (+5pp 以上): ネットスコアが前日比で改善
- **警戒** (-5pp 以下): ネットスコアが前日比で悪化
- **強い変動** (±15pp 超): レポート本文に変動理由が必須

### 4. 観点鮮度警告

各銘柄の `criteria_age_days` を確認:

| 日数 | マーク | 推奨アクション |
|------|--------|----------------|
| < 90日 | （表示なし） | OK |
| 90〜179日 | 🟡 | `/etf-rating tune {code}` で見直し検討 |
| ≥ 180日 | 🔴 | 早急に tune 必須（採点信頼性低下） |

### 5. カテゴリ別集計

target_holdings の `bucket`（group_a / group_b）別に平均スコアを集計:

| グループ | 銘柄数 | 平均ネット | 平均上昇W | 平均下落W |
|---|---:|---:|---:|---:|
| A群（コア・ヘッジ） | 3 | XX.X | XX.X | XX.X |
| B群（日本株テーマ） | 4 | XX.X | XX.X | XX.X |

### 6. 総評（300字以内）

> **文体・用語制約**: 総評は最終的にメール本文「今日のひとこと」として
> 表示される。phase3-mail-payload.md の文体ガイド（です・ます調・尊敬語/
> 謙譲語禁止・内部スコア名「上昇W／下落W／ネット中期スコア」は本文中で
> 使わず「追い風スコア／下落リスク／総合点」等の言い換え）を必ず適用する。
> 言い換え表の SSOT は phase3-mail-payload.md の「内部用語→平易表現 言い換え表」を参照。

以下の要素を1段落で:

- 市況判定（Phase 0 snapshot より）
- 最高ネット銘柄・最低ネット銘柄
- A群 vs B群の傾向
- 注目すべきハイライト1〜2件

### 7. 出力ファイル生成

以下を Write:
- `{WORK_DIR}/20_daily_summary.md`（作業用）
- `reports/etf-rating/_daily_summary/{YYYYMMDD}.md`（公開先、同一内容）

#### 出力フォーマット

```markdown
# ETF Rating 集計サマリ（{RUN_DATE}）

**評価銘柄数**: {N}
**実行時刻**: {ISO8601}
**市況判定**: リスクオン / 中立 / リスクオフ（Phase 0 snapshot 引用）

---

## 総評

{300字以内の総評}

---

## ランキング

| 順位 | コード | 銘柄名 | ネット | 上昇W | 下落W | 先取り | 後追い | 前日比 | 鮮度 |
|---:|---|---|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1629 | 商社 | 67.4 | 71.9 | 37.2 | +28.0 | +37.0 | +2.1 | |

---

## ハイライト

### 強気転換（前日比 +5pp 以上）
- {code} {name}: +N.Npp（主因: ...）

### 警戒（前日比 -5pp 以下）
- {code} {name}: -N.Npp（主因: ...）

### 強い変動（±15pp 超、要本文確認）
- {code}: ネット {prev} → {curr}、理由は本文参照

---

## カテゴリ別

| グループ | 銘柄数 | 平均ネット | 平均上昇W | 平均下落W | コメント |
|---|---:|---:|---:|---:|---|
| A群 | 3 | XX.X | XX.X | XX.X | ... |
| B群 | 4 | XX.X | XX.X | XX.X | ... |

---

## 観点鮮度警告

| コード | version | 経過日数 | マーク | 推奨アクション |
|---|---|---:|:---:|---|
| ... | ... | ... | 🟡/🔴 | ... |

警告なしの場合: 「全銘柄が90日以内に更新済み」と明記

---

## 銘柄別レポートへのリンク

- [1629 商社](../1629/{YYYYMMDD}_1629_rating.md)
- ...

---

## データソース

- Phase 0 市場スナップショット: `{WORK_DIR}/00_market_snapshot.md`
- 採点履歴: `data/etf-rating/history/`
```

### 8. Phase 3 用フラグ出力

**flags 集約ルール**: 各 `10_rating_*_summary.json` の `flags_self` フィールド
（Phase 1 の 10a節で生成）を全て concat して `flags` 配列にまとめる。
判定ロジックは Phase 1 で完結しており、Phase 2 ではそのまま集約のみ行う
（しきい値の再評価はしない）。`flags_self` 欠損銘柄は空配列扱いで続行。

`{WORK_DIR}/20_summary_meta.json` を Write（Phase 3 メールペイロード生成用）:

```json
{
  "run_date": "{RUN_DATE}",
  "etf_count": N,
  "avg_net_score": NN.N,
  "bullish_turn_count": N,
  "warning_count": N,
  "market_regime": "リスクオン|中立|リスクオフ",
  "ranking": [{"code": "...", "name": "...", "net_score": NN.N, "delta": +/-N.N}, ...],
  "flags": [
    {"code": "...", "type": "strong_tailwind", "upside_weighted": NN.N}
  ],
  "highlights": {
    "bullish_turn": [{"code": "...", "delta": +N.N, "reason": "..."}],
    "warning": [{"code": "...", "delta": -N.N, "reason": "..."}],
    "strong_change": [{"code": "...", "delta": +/-NN.N}]
  },
  "criteria_age_warnings": [
    {"code": "...", "version": "...", "age_days": NN, "mark": "yellow|red"}
  ],
  "group_summary": {
    "group_a": {"count": 3, "avg_net": NN.N},
    "group_b": {"count": 4, "avg_net": NN.N}
  },
  "report_paths": {
    "{code}": "reports/etf-rating/{code}/{YYYYMMDD}_{code}_rating.md",
    ...
  }
}
```

## 出力

| ファイル | 内容 |
|----------|------|
| `{WORK_DIR}/20_daily_summary.md` | 集計サマリ（作業用） |
| `{WORK_DIR}/20_summary_meta.json` | Phase 3 用メタデータ |
| `reports/etf-rating/_daily_summary/{YYYYMMDD}.md` | 公開先 |

## メインへの戻り値

完了時1行:
```
集計完了（強気 {N1}銘柄 / 警戒 {N2}銘柄 / 鮮度警告 {N3}件）
```

失敗時1行:
```
集計失敗: {理由}
```

## 自己修正ルール

- 一部 summary.json が欠損 → 該当銘柄は「データ取得不可」で集計に含めて続行
- 履歴 jsonl が空（初回実行） → 前日比は `null` 扱いでハイライト出力スキップ
