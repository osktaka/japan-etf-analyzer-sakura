# Phase 1: 単一銘柄評価

## 目的

1銘柄について criteria YAML に定義された「上昇10条件 × 下落10条件」を
現在の市場情勢にマッチングさせて 0〜100 点で採点し、Top5 ドライバーに
重み×2 をかけてネット中期スコア・先取り/後追い区分・3シナリオまでをまとめる。

参考実装: `reports/research/1629_evaluation_20260522.md`（採点フォーマットの正解例）

## 入力パラメータ

| パラメータ | 説明 | 例 |
|------------|------|-----|
| `WORK_DIR` | 作業ディレクトリ | `.tmp/etf-rating_20260522` |
| `CODE` | 評価対象 ETF コード | `1629` |
| `CRITERIA_PATH` | 観点 YAML | `.claude/skills/etf-rating/criteria/1629.yaml` |
| `MARKET_SNAPSHOT` | Phase 0 出力 | `{WORK_DIR}/00_market_snapshot.md` |
| `CALC_PARAMS_PATH` | 共通閾値 JSON | `.claude/skills/etf-rating/calc_params.json` |
| `RUN_DATE` | 実行日（YYYY-MM-DD） | `2026-05-22` |
| `HISTORY_PATH` | 採点履歴 jsonl | `data/etf-rating/history/{CODE}.jsonl` |

## 検索バジェット

`calc_params.json` の `web_search.phase1_per_etf_search_budget`（既定3回）まで。
Phase 0 スナップショットで足りる項目は再検索しない。

## 株価取得の厳守ルール

CLAUDE.md「株式分割の管理」と auto-memory に従う:

1. 現在株価・直近終値・モメンタムは **必ず API 経由** で取得
   - `curl http://localhost:8902/api/v1/chart/{CODE}?period=3mo` 等
2. SQLite 直接クエリで `trades` / `price_data` を読んで計算に使うことを禁止
3. 対象銘柄の `stock_splits` を事前確認

## 手順

### 1. 設定・観点読み込み

- `CRITERIA_PATH` を Read（YAML）。欠損なら戻り値「{CODE} スキップ: criteria 欠損」で終了
- `CALC_PARAMS_PATH` を Read（JSON）
- `MARKET_SNAPSHOT` を Read（Phase 0 出力。失敗時はその旨記録して続行）

### 2. 株価データ取得

API 経由で以下を取得し、`{WORK_DIR}/10_data_{CODE}.json` に保存:

- 直近終値・前日比・1週間/1ヶ月/3ヶ月リターン
- 過去最高値・現在値の乖離率
- 200日移動平均・乖離率
- ATR(14)・出来高直近5日平均

### 3. 個別ニュース・固有材料の補完検索（WebSearch）

`CRITERIA_PATH` の `top5_drivers` / `top5_risk_drivers` のうち、Phase 0
スナップショットで未カバーの項目について、**最大3クエリ**で個別検索。

例（1629 の場合）:
- 「三菱商事 / 三井物産 自社株買い 2026」
- 「Buffett Berkshire 商社 保有比率 2026」

### 4. 上昇10条件の採点（A-1〜A-10）

criteria YAML の `upside_conditions` 各項目について、以下を実施:

1. `thresholds` フィールドの数値判定（あれば自動採点の根拠とする）
2. Phase 0 スナップショット + Step 3 検索結果を参照し、0〜100 点で採点
3. `type` フィールドで先取り（`leading`）/ 後追い（`lagging`）/ 混在を区別
4. 重み: `top5_drivers` 列挙の条件は ×2、それ以外は ×1

#### 4a. thresholds → 0〜100 採点マッピング（自動採点アルゴリズム）

`thresholds` に数値ベース閾値（`strong_bullish` / `bullish` / `neutral` / `bearish`）が
あれば、現在値を当てはめて以下の基準スコアを割り当てる:

| 閾値帯 | 基準スコア | 補足 |
|--------|-----------:|------|
| `strong_bullish` 該当 | 85 | 帯内で上に行くほど 85〜95 で内挿可 |
| `bullish` 該当 | 70 | 帯内で 70〜84 で内挿可 |
| `neutral` 該当 | 50 | 帯内で 40〜65 で内挿可 |
| `bearish` 該当 | 25 | 帯内で 10〜39 で内挿可 |

**複数指標がある場合**: 各指標の基準スコアを単純平均（または criteria に重み指定があればそれに従う）。

**定性のみの場合**（thresholds に明確な数値帯がない / 抽象指標）:
- 🟢 強い追い風 → 75〜85
- 🟡 中立〜やや追い風 → 50〜69
- 🔴 中立を下回る → 20〜39

#### 4b. 採点ガイドライン（最終調整）

自動採点の基準スコアに、定性情報（地政学・要人発言・需給など）で±10点の調整を加えてよい:

- **80点以上**: 条件をほぼ完全に満たし強い追い風
- **70〜79点**: 強い追い風（`strong_bullish_threshold` 以上）
- **50〜69点**: 中立〜やや追い風
- **30〜49点**: 中立を下回る、わずかな追い風喪失
- **30点未満**: 条件が成立していない、または逆風

### 5. 下落10条件の採点（B-1〜B-10）

criteria YAML の `downside_conditions` 各項目について同様に採点。
**高得点 = リスク大** で採点する点に注意:

- 80点以上: 重大リスクが顕在化
- 70〜79点: 警戒（`warning_threshold` 以上）
- 50〜69点: 中程度
- 30〜49点: 軽微
- 30点未満: ほぼ無視可能

### 6. 集計計算

| 指標 | 計算式 |
|------|--------|
| 上昇単純平均 | Σ(A-1〜A-10) / 10 |
| 上昇重み付け | Σ(score × weight) / Σ(weight) ※Top5は×2 |
| 下落単純平均 | Σ(B-1〜B-10) / 10 |
| 下落重み付け | Σ(score × weight) / Σ(weight) |
| 先取りネット | 上昇先取り平均 − 下落先取り平均 |
| 後追いネット | 上昇後追い平均 − 下落後追い平均 |
| **ネット中期スコア** | 上昇重み付け + (100 − 下落重み付け) |

### 7. 3シナリオ生成

criteria YAML の `scenarios.base` / `upside` / `downside` をテンプレに、
Phase 0 スナップショット・採点結果から **想定値幅（%レンジ）** を埋める。

例:
- 維持シナリオ（base）: +5〜+15%
- 上振れシナリオ（upside）: +20〜+35%
- 下振れシナリオ（downside）: -15〜-25%

### 8. 前日比チェック（履歴比較）

`HISTORY_PATH`（`data/etf-rating/history/{CODE}.jsonl`）の末尾行を Read し、
前回採点と比較。`calc_params.json` の `drift_alert`:

- `score_change_pp_threshold`（既定5pp）超: サマリの「ハイライト」候補
- `score_change_pp_strong_threshold`（既定15pp）超: レポート本文に **変動理由を必須明記**

### 9. レポート生成

`{WORK_DIR}/10_rating_{CODE}.md` および
`reports/etf-rating/{CODE}/{YYYYMMDD}_{CODE}_rating.md`（同一内容）を Write。

#### 出力フォーマット

```markdown
# {CODE}（{name}）中期マッチ度評価

**作成日**: {RUN_DATE}
**評価対象**: {name}（{構成概要}）
**評価時間軸**: 中期（3〜12ヶ月）
**現在株価**: {price}円（{date}終値）
**criteria version**: {version}（{age_days}日前）{warning_mark}

---

## エグゼクティブサマリ

| 指標 | スコア（100満点） | 中央値 | 解釈 |
|---|---:|---|---|
| 上昇条件マッチ度（重み付け） | {NN.N} | 50 | ... |
| 下落リスク度（重み付け） | {NN.N} | 50 | ... |
| ネット中期スコア | {NNN.N}/200 = {NN.N} | 100 | ... |
| 先取り情報スコア | +{NN.N} | 0 | ... |
| 後追い情報スコア | +{NN.N} | 0 | ... |

**前日比**: ネット {+/-N.N}pp / 上昇 {+/-N.N}pp / 下落 {+/-N.N}pp
{変動理由（前日比±15pp超時のみ）}

**結論一言**: ...

---

## 1. 採点ルール
（共通文言）

## 2. 上昇条件 × 現在情勢 マッチング採点

| # | 上昇条件 | 過去事例 | 現在の状況 | 区分 | 重み | スコア |
|---|---|---|---|---|---:|---:|
| A-1 | ... | ... | 🟢/🟡/🔴 ... | 先取り/後追い | ×1/×2 | NN |
| ... |

### 上昇条件 集計
| 集計軸 | 値 |
|---|---:|
| 単純平均 | XX.X |
| 重み付け | XX.X |

## 3. 下落条件 × 現在情勢 マッチング採点
（同様）

## 4. 総合スコアと先取り/後追い区分

## 5. Top5 ドライバー詳細

## 6. シナリオ

### 維持シナリオ（base）
- 想定値幅: +X〜+X%
- 前提: ...

### 上振れシナリオ（upside）
### 下振れシナリオ（downside）

## 7. 結論と推奨スタンス

## 8. データソース

- 株価: ChartService API（分割調整済み）
- マクロ: `{WORK_DIR}/00_market_snapshot.md`（Phase 0）
- 個別ニュース: WebSearch（{N}クエリ）
```

### 10. 履歴追記

`data/etf-rating/history/{CODE}.jsonl` に1行追記する。ディレクトリ作成 → jq で
JSONを組み立て → `>>` で末尾追記、を Bash 1ブロックで実行する:

```bash
# 必須: 11フィールド（date / code / net_score / upside_weighted / downside_weighted /
#                    leading_net / lagging_net / criteria_version / criteria_age_days /
#                    upside_avg / downside_avg）
HIST_DIR="data/etf-rating/history"
HIST_FILE="${HIST_DIR}/{CODE}.jsonl"
mkdir -p "${HIST_DIR}"
jq -nc \
  --arg date "{YYYYMMDD}" \
  --arg code "{CODE}" \
  --arg version "{criteria_version}" \
  --argjson net "{net_score}" \
  --argjson up_w "{upside_weighted}" \
  --argjson dn_w "{downside_weighted}" \
  --argjson lead "{leading_net}" \
  --argjson lag "{lagging_net}" \
  --argjson up_avg "{upside_avg}" \
  --argjson dn_avg "{downside_avg}" \
  --argjson age "{criteria_age_days}" \
  '{date:$date, code:$code, net_score:$net, upside_weighted:$up_w,
    downside_weighted:$dn_w, leading_net:$lead, lagging_net:$lag,
    upside_avg:$up_avg, downside_avg:$dn_avg,
    criteria_version:$version, criteria_age_days:$age}' \
  >> "${HIST_FILE}"
```

**同日2回目以降の実行（冪等性）**: 同日 `date` が既に末尾にある場合は追記前に
最終行を削除する:

```bash
if tail -n 1 "${HIST_FILE}" 2>/dev/null | jq -e --arg d "{YYYYMMDD}" '.date == $d' > /dev/null; then
  sed -i '$ d' "${HIST_FILE}"
fi
# 上記の jq -nc ... >> "${HIST_FILE}" を続けて実行
```

**生成例（1629 の場合）**:
```json
{"date":"20260522","code":"1629","net_score":67.4,"upside_weighted":71.9,"downside_weighted":37.2,"leading_net":28.0,"lagging_net":37.0,"upside_avg":70.9,"downside_avg":35.8,"criteria_version":"2026-05-22_v1","criteria_age_days":0}
```

### 10a. flags 生成ルール（Phase 1 が責務）

各銘柄の集計結果から、Phase 2 のメール件名・本文集計・notifier 件名再構築に
使う `flags` リスト要素を **Phase 1 サマリ JSON に同梱** する。判定基準は
`calc_params.json` を参照する（ハードコード禁止）。

| 条件 | 出力 type | 参照閾値 |
|------|-----------|----------|
| `upside_weighted >= scoring.strong_bullish_threshold`（既定70） | `strong_tailwind` | `scoring.strong_bullish_threshold` |
| `downside_weighted >= scoring.warning_threshold`（既定70） | `severe_risk` | `scoring.warning_threshold` |
| `net_score < scoring.neutral`（中立=50を下回る・※将来30未満などに微調整可） | `critical_risk` | `scoring.neutral` |

出力スキーマ:
```json
{"code": "<code>", "type": "strong_tailwind|severe_risk|critical_risk",
 "upside_weighted": <値>, "downside_weighted": <値>, "net_score": <値>}
```

**責務境界**:
- **Phase 1**: 各銘柄の summary.json に `flags_self` フィールドとして自銘柄分の flags 要素を出力
- **Phase 2**: 全銘柄の `flags_self` を集約して `flags` リストにまとめ、20_summary_meta.json に格納
- **Phase 3**: `flags` を email_payload.json の `flags` キーへそのまま転載

これにより notifier 側の `_count_flag_types()` が件名再集計で参照する `type` 値が
全 Phase で一貫し、過去発生した「強0警0」固定文字列バグの再発を防ぐ。

### 11. 出力サマリ

`{WORK_DIR}/10_rating_{CODE}_summary.json` を Write（Phase 2 集計用）:

```json
{
  "code": "{CODE}",
  "name": "{name}",
  "net_score": NN.N,
  "upside_weighted": NN.N,
  "downside_weighted": NN.N,
  "leading_net": NN.N,
  "lagging_net": NN.N,
  "delta_from_prev": {"net": +/-N.N, "upside": +/-N.N, "downside": +/-N.N},
  "criteria_version": "{version}",
  "criteria_age_days": NN,
  "top_drivers_bullish": ["A-X", "A-Y", ...],
  "top_drivers_bearish": ["B-X", "B-Y", ...],
  "flags_self": [
    {"code": "{CODE}", "type": "strong_tailwind", "upside_weighted": 76.0}
  ],
  "report_path": "reports/etf-rating/{CODE}/{YYYYMMDD}_{CODE}_rating.md"
}
```

`flags_self` は **10a 節のルール**で判定（複数該当時は配列に複数要素）。
該当なしなら `[]` を出力。

## 出力

| ファイル | 内容 |
|----------|------|
| `{WORK_DIR}/10_data_{CODE}.json` | API 取得した価格データ |
| `{WORK_DIR}/10_rating_{CODE}.md` | 評価レポート（作業用コピー） |
| `{WORK_DIR}/10_rating_{CODE}_summary.json` | Phase 2 集計用サマリ |
| `reports/etf-rating/{CODE}/{YYYYMMDD}_{CODE}_rating.md` | 公開レポート |
| `data/etf-rating/history/{CODE}.jsonl` | 履歴1行追記 |

## メインへの戻り値

完了時1行:
```
{CODE} 完了（ネット {NN.N}/100, 前日比 {+/-N.N}pp）
```

スキップ時1行:
```
{CODE} スキップ: {理由}
```

## 自己修正ルール

完了判定 No を返す前に **1回だけ**自己修正を試みる:
- API レスポンス欠損 → 別期間で再取得（`period=6mo` 等）
- WebSearch 結果不足 → クエリを言い換えて1回追加（バジェット内なら）
- 計算結果が直感と乖離 → 株式分割未調整を疑い API 出力を再確認

それでも失敗の場合のみメインに失敗報告。
